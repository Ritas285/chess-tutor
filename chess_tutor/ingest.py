"""Ingestione (offline): documenti di un ramo -> chunk -> embedding -> Qdrant. (Step 1a, metodo della lezione S07)

La RAG ha DUE TEMPI:
  1. OFFLINE, una volta: Parser -> Splitter -> Embedder -> Vector store   (questo file)
  2. QUERY-TIME, a ogni domanda: embedding della domanda -> ricerca -> risposta   (da Step 1b/1c)

Ogni ramo ha la sua collection (chess_<ramo>): l'agente cercherà solo in quella del ramo scelto.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from datapizza.core.vectorstore import VectorConfig
from datapizza.embedders import ChunkEmbedder
from datapizza.embedders.openai import OpenAIEmbedder
from datapizza.modules.parsers.md_parser import MDParser
from datapizza.modules.splitters import RecursiveSplitter
from datapizza.pipeline import IngestionPipeline
from datapizza.vectorstores.qdrant import QdrantVectorstore

from . import config


def nome_collection(ramo: str) -> str:
    return f"chess_{ramo}"


def crea_embedder() -> OpenAIEmbedder:
    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY non impostata: copia .env.example in .env e inserisci la tua chiave.")
    return OpenAIEmbedder(api_key=config.OPENAI_API_KEY, model_name=config.EMB_MODEL)


def crea_vector_store() -> QdrantVectorstore:
    """Qdrant in memoria, come in S06-S08: nessun Docker, l'indice vive finché vive il programma."""
    return QdrantVectorstore(location=":memory:")


def prepara_collection(vs: QdrantVectorstore, ramo: str) -> str:
    """Crea la collection del ramo, PARTENDO DA ZERO.

    Il reset serve davvero (nota di S11): il RecursiveSplitter dà ai chunk un id nuovo a ogni esecuzione, quindi
    ri-indicizzare senza cancellare accumula chunk duplicati (stesso testo, id diversi).
    """
    nome = nome_collection(ramo)
    if vs.get_client().collection_exists(nome):
        vs.delete_collection(nome)
    vs.create_collection(collection_name=nome,
                         vector_config=[VectorConfig(dimensions=config.EMB_DIM, name=config.EMB_NAME)])
    return nome


def documenti_del_ramo(ramo: str, data_dir: Path | None = None) -> list[Path]:
    return sorted(((data_dir or config.DATA_DIR) / ramo).glob("*.md"))


def indicizza_ramo(vs: QdrantVectorstore, embedder, ramo: str, data_dir: Path | None = None, verbose: bool = True) -> int:
    """Indicizza tutti i documenti di un ramo. Ritorna quanti documenti ha letto."""
    nome = prepara_collection(vs, ramo)
    pipeline = IngestionPipeline(
        modules=[
            MDParser(),                                                       # legge il Markdown rispettando i titoli
            RecursiveSplitter(max_char=config.CHUNK_MAX_CHAR, overlap=config.CHUNK_OVERLAP),   # spezza in chunk
            ChunkEmbedder(client=embedder, embedding_name=config.EMB_NAME),   # chunk -> numeri
        ],
        vector_store=vs,
        collection_name=nome,
    )
    files = documenti_del_ramo(ramo, data_dir)
    for f in files:
        # `source_file` NON si compila da solo: va passato qui. Senza, niente citazioni delle fonti (S07/S11).
        pipeline.run(file_path=str(f), metadata={"source_file": f.name, "ramo": ramo})
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
        anteprima = h.text.replace("\n", " ")[:110]
        print(f"  {i}. [{h.metadata.get('source_file', '?')}] {anteprima}…")


if __name__ == "__main__":
    main()
