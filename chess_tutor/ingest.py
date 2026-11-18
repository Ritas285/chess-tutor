"""Ingestione (offline): documenti di un ramo -> chunk -> embedding -> Qdrant. (Step 1a, metodo della lezione S07)

La RAG ha DUE TEMPI:
  1. OFFLINE, una volta: Parser -> Splitter -> Embedder -> Vector store   (questo file)
  2. QUERY-TIME, a ogni domanda: embedding della domanda -> ricerca -> risposta   (da Step 1b/1c)

Ogni ramo ha la sua collection (chess_<ramo>): l'agente cercherà solo in quella del ramo scelto.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

from datapizza.core.models import PipelineComponent
from datapizza.core.vectorstore import VectorConfig
from datapizza.embedders import ChunkEmbedder
from datapizza.embedders.openai import OpenAIEmbedder
from datapizza.modules.parsers.md_parser import MDParser
from datapizza.modules.splitters import NodeSplitter
from datapizza.pipeline import IngestionPipeline
from datapizza.vectorstores.qdrant import QdrantVectorstore

from . import config
from .pdf import LeggiPdf


def nome_collection(ramo: str) -> str:
    return f"chess_{ramo}"


def _solo_lettere_e_cifre(testo: str) -> str:
    """Forma "grezza" per riconoscere dove sta un pezzo nel file: senza spazi, punteggiatura e simboli dell'elenco."""
    return re.sub(r"[^a-z0-9]", "", testo.lower())


class AggiungiTitolo(PipelineComponent):
    """Passaggio della pipeline (tra splitter ed embedder): mette davanti a ogni pezzo "[titolo — sezione]".

    PERCHÉ: il parser del corso riconosce le sezioni ma BUTTA VIA il testo dei titoli, quindi un pezzo come "Il cavallo si
    muove a L…" non sa più di cosa parla. Anteporre il titolo PRIMA dell'embedding è il *contextual retrieval* di S08:
    il pezzo "porta con sé" il contesto, sia per la ricerca per significato sia per quella per parole.
    Prima di ogni file va chiamato `carica(percorso)`: legge titolo e sezioni dal file.
    """

    def __init__(self):
        self.titolo: str = ""
        self.sezioni: list[tuple[str, str]] = []

    def carica(self, percorso: Path) -> None:
        testo = percorso.read_text(encoding="utf-8")
        self.titolo = (re.search(r"^#\s+(.+)$", testo, re.M) or [None, percorso.stem])[1].strip()
        parti = re.split(r"^##\s+", testo, flags=re.M)
        intro = re.sub(r"^#\s+.+$", "", parti[0], flags=re.M)
        self.sezioni = [("Introduzione", _solo_lettere_e_cifre(intro))]
        for p in parti[1:]:
            nome, _, corpo = p.partition("\n")
            self.sezioni.append((nome.strip(), _solo_lettere_e_cifre(corpo)))

    def _sezione_di(self, testo: str) -> str:
        inizio = _solo_lettere_e_cifre(testo)[:40]
        return next((nome for nome, corpo in self.sezioni if inizio and inizio in corpo), "")

    def _run(self, chunks):
        for c in chunks:
            sezione = self._sezione_di(c.text)
            c.metadata = {**(c.metadata or {}), "titolo": self.titolo, "sezione": sezione}
            c.text = f"[{self.titolo} — {sezione}]\n{c.text}" if sezione else f"[{self.titolo}]\n{c.text}"
        return chunks

    async def _a_run(self, chunks):
        return self._run(chunks)


def etichetta(chunk) -> str:
    """Come citare un pezzo: "01_pezzi_e_movimenti.md › Il cavallo"."""
    fonte, sezione = chunk.metadata.get("source_file", "?"), chunk.metadata.get("sezione", "")
    return f"{fonte} › {sezione}" if sezione else fonte


def anteprima(chunk, n: int = 150) -> str:
    """Le prime n lettere del testo del pezzo, SENZA la riga d'intestazione (quella la mostra l'etichetta)."""
    corpo = chunk.text.split("\n", 1)[1] if chunk.text.startswith("[") and "\n" in chunk.text else chunk.text
    return corpo.replace("\n", " ")[:n]


def crea_embedder() -> OpenAIEmbedder:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY non impostata: copia .env.example in .env e inserisci la tua chiave.")
    return OpenAIEmbedder(api_key=config.OPENAI_API_KEY, model_name=config.EMB_MODEL)


def crea_vector_store() -> QdrantVectorstore:
    """Qdrant in memoria, come in S06-S08: nessun Docker, l'indice vive finché vive il programma."""
    return QdrantVectorstore(location=":memory:")


def prepara_collection(vs: QdrantVectorstore, ramo: str) -> str:
    """Crea la collection del ramo, PARTENDO DA ZERO.

    Il reset serve davvero (nota di S11): gli splitter danno ai chunk un id nuovo a ogni esecuzione, quindi
    ri-indicizzare senza cancellare accumula chunk duplicati (stesso testo, id diversi).
    """
    nome = nome_collection(ramo)
    if vs.get_client().collection_exists(nome):
        vs.delete_collection(nome)
    vs.create_collection(collection_name=nome,
                         vector_config=[VectorConfig(dimensions=config.EMB_DIM, name=config.EMB_NAME)])
    return nome


def documenti_del_ramo(ramo: str, data_dir: Path | None = None) -> list[Path]:
    """I documenti del ramo: .md (sempre) e .pdf (solo nei rami PDF, i cui file non stanno nel git)."""
    cartella = (data_dir or config.DATA_DIR) / ramo
    return sorted([*cartella.glob("*.md"), *cartella.glob("*.pdf")], key=lambda p: p.name.lower())   # stesso ordine su Windows e Linux


def indicizza_ramo(vs: QdrantVectorstore, embedder, ramo: str, data_dir: Path | None = None, verbose: bool = True) -> int:
    """Indicizza tutti i documenti di un ramo. Ritorna quanti documenti ha letto."""
    nome = prepara_collection(vs, ramo)
    titolatore = AggiungiTitolo()
    pipeline_md = IngestionPipeline(
        modules=[
            MDParser(),                                                  # legge il Markdown e ne riconosce le sezioni
            NodeSplitter(max_char=config.CHUNK_MAX_CHAR),                # una sezione = un pezzo
            titolatore,                                                  # "[titolo — sezione]" davanti al pezzo
            ChunkEmbedder(client=embedder, embedding_name=config.EMB_NAME),   # pezzo -> numeri
        ],
        vector_store=vs,
        collection_name=nome,
    )
    pipeline_pdf = IngestionPipeline(                                    # un PDF non ha sezioni: pezzi per pagina (chess_tutor/pdf.py)
        modules=[LeggiPdf(), ChunkEmbedder(client=embedder, embedding_name=config.EMB_NAME)],
        vector_store=vs,
        collection_name=nome,
    )
    files = documenti_del_ramo(ramo, data_dir)
    for f in files:
        # `source_file` NON si compila da solo: va passato qui. Senza, niente citazioni delle fonti (S07/S11).
        if f.suffix.lower() == ".pdf":
            pipeline_pdf.run(file_path=str(f), metadata={"source_file": f.name, "ramo": ramo})
        else:
            titolatore.carica(f)
            pipeline_md.run(file_path=str(f), metadata={"source_file": f.name, "ramo": ramo})
        if verbose:
            print(f"  indicizzato: {ramo}/{f.name}")
    return len(files)


def chunk_del_ramo(vs: QdrantVectorstore, ramo: str) -> list:
    return list(vs.dump_collection(nome_collection(ramo)))


def statistiche(vs: QdrantVectorstore, ramo: str) -> dict:
    """Quanti chunk e quanto lunghi: serve a ragionare sulle manopole del chunking."""
    lunghezze = [len(c.text) for c in chunk_del_ramo(vs, ramo)]
    return {"chunk": len(lunghezze), "media": sum(lunghezze) // max(len(lunghezze), 1), "max": max(lunghezze, default=0)}


def cerca(vs: QdrantVectorstore, embedder, ramo: str, domanda: str, k: int = 3) -> list:
    """Solo per provare l'indice: la domanda va DIRETTA all'embedder (nessun LLM la tocca) e si prendono i k chunk più vicini."""
    vettore = embedder.embed(domanda)
    return vs.search(collection_name=nome_collection(ramo), query_vector=vettore, k=k, vector_name=config.EMB_NAME)


def main() -> None:
    ap = argparse.ArgumentParser(description="Indicizza un ramo e prova una ricerca. Serve OPENAI_API_KEY (costo: frazioni di centesimo).")
    ap.add_argument("domanda", nargs="?", default="Come funziona l'arrocco?")
    ap.add_argument("--ramo", default="rules", choices=list(config.BRANCHES))
    ap.add_argument("-k", type=int, default=3)
    args = ap.parse_args()

    embedder, vs = crea_embedder(), crea_vector_store()
    print(f"Indicizzo il ramo '{args.ramo}'…")
    n = indicizza_ramo(vs, embedder, args.ramo)
    print(f"{n} documenti -> {statistiche(vs, args.ramo)}\n")
    print(f"Domanda: {args.domanda}")
    for i, h in enumerate(cerca(vs, embedder, args.ramo, args.domanda, args.k), 1):
        print(f"  {i}. [{etichetta(h)}] {anteprima(h)}…")


if __name__ == "__main__":
    main()
