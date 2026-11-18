"""Finti per i test: embedder e client LLM scriptati. Nessuna chiave, nessuna rete."""
import hashlib
import math

from datapizza.core.clients import Client, ClientResponse
from datapizza.core.clients.models import TokenUsage
from datapizza.core.embedder import BaseEmbedder
from datapizza.type import FunctionCallBlock, FunctionCallResultBlock, StructuredBlock, TextBlock

import re

from chess_tutor import config
from chess_tutor.router import RouteOut


class HashEmbedder(BaseEmbedder):
    """Trasforma un testo in 1536 numeri contando le parole (hash). Non capisce il significato:
    basta a verificare che l'ingestione e la ricerca siano collegate bene."""

    def __init__(self):
        super().__init__(model_name="hash")

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * config.EMB_DIM
        for parola in text.lower().split():
            v[int(hashlib.md5(parola.encode()).hexdigest(), 16) % config.EMB_DIM] += 1.0
        norma = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / norma for x in v]

    def embed(self, text, model_name=None, **kw):
        return self._vec(text) if isinstance(text, str) else [self._vec(t) for t in text]


class ScriptedClient(Client):
    """Un finto LLM. Come router risponde con la decisione indicata. Come agente: al 1° giro chiama il primo strumento
    disponibile con la domanda; al 2° risponde citando il risultato dello strumento.
    `calls` registra gli strumenti chiamati dall'agente; `structured_calls` quante volte è stato interpellato il router."""

    def __init__(self, route: RouteOut | None = None):
        super().__init__(model_name="fake", system_prompt="")
        self.route = route or RouteOut(about_chess=True, branches=["rules"], confidence=0.9)
        self.calls: list[str] = []
        self.structured_calls = 0

    def _question(self, input, memory):
        for blk in reversed(list(input or [])):
            if isinstance(blk, TextBlock):
                return blk.content
        for turn in reversed(list(memory.memory if memory else [])):
            for blk in turn:
                if isinstance(blk, TextBlock):
                    return blk.content
        return ""

    def _tool_results(self, memory, input):
        out = []
        for blk in list(input or []):
            if isinstance(blk, FunctionCallResultBlock):
                out.append(blk.result)
        for turn in (memory.memory if memory else []):
            for blk in turn:
                if isinstance(blk, FunctionCallResultBlock):
                    out.append(blk.result)
        return out

    def _invoke(self, input, tools=None, memory=None, tool_choice="auto", temperature=None, max_tokens=None,
                system_prompt=None, **kw):
        results = self._tool_results(memory, input)
        usage = TokenUsage(prompt_tokens=100, completion_tokens=20)
        if not results and tools and "RICERCA INIZIALE" in self._question(input, memory):
            # I passaggi sono già sotto la domanda (Tutor.ricerca_iniziale): come il modello vero, risponde senza chiamare lo strumento.
            riga = next((r for r in self._question(input, memory).splitlines() if r.startswith("[") and "›" in r), "[fonte]")
            return ClientResponse(content=[TextBlock(content=f"Risposta di prova. Fonte: {riga}")], usage=usage)
        if not results and tools:
            tool = tools[0]
            self.calls.append(tool.name)
            q = self._question(input, memory)
            args = {p: q for p in tool.properties} if getattr(tool, "properties", None) else {"domanda": q}
            return ClientResponse(content=[FunctionCallBlock(id="c1", name=tool.name, arguments=args, tool=tool)], usage=usage)
        corpo = str(results[-1]) if results else "nessun documento"
        riga = next((r for r in corpo.splitlines() if r.startswith("[")), "[fonte]")
        return ClientResponse(content=[TextBlock(content=f"Risposta di prova. Fonte: {riga}")], usage=usage)

    def _structured_response(self, input, output_cls=None, memory=None, temperature=None, max_tokens=None,
                             system_prompt=None, tools=None, tool_choice="auto", **kw):
        self.structured_calls += 1
        return ClientResponse(content=[StructuredBlock(content=self.route)], usage=TokenUsage(prompt_tokens=50, completion_tokens=10))

    async def _a_invoke(self, *a, **k): return self._invoke(*a, **k)
    async def _a_structured_response(self, *a, **k): return self._structured_response(*a, **k)
    def _stream_invoke(self, *a, **k): raise NotImplementedError
    async def _a_stream_invoke(self, *a, **k): raise NotImplementedError
    def _convert_tool_choice(self, tool_choice): return {}


class ModelloIngenuo(ScriptedClient):
    """Simula un modello che CASCA nell'injection: nella risposta riporta ogni link che trova nei passaggi (come un'immagine
    markdown che fa uscire dati), aggiunge un segreto e una citazione inventata. Serve al RETEST di S15: cosa fermano le barriere?"""

    def _invoke(self, input, tools=None, memory=None, **kw):
        risultati = self._tool_results(memory, input)
        if not risultati and "RICERCA INIZIALE" in self._question(input, memory):
            risultati = [self._question(input, memory)]      # i passaggi stanno sotto la domanda: il modello ingenuo li legge lo stesso
        if not risultati:
            return super()._invoke(input, tools=tools, memory=memory, **kw)
        link = re.findall(r"https?://[^\s)\"']+", str(risultati[-1]))
        testo = ("L'arrocco serve a proteggere il re. " + " ".join(f"![x]({u})" for u in link)
                 + " Invio la chat a audit@collector.example. password: hunter2 [fantasma.md]")
        return ClientResponse(content=[TextBlock(content=testo)], usage=TokenUsage(prompt_tokens=100, completion_tokens=20))


class ClienteStrutturato(ScriptedClient):
    """Un finto LLM che per ogni modulo (output_cls) restituisce l'oggetto indicato in `risposte`: es. {QuizSet: ..., Giudizio: ...}.
    `visti` registra, per modulo, i testi ricevuti. Un valore che è un'eccezione viene sollevato (per simulare un servizio giù)."""

    def __init__(self, risposte: dict, route=None):
        super().__init__(route=route)
        self.risposte, self.visti = risposte, {}

    def _structured_response(self, input, output_cls=None, memory=None, temperature=None, max_tokens=None,
                             system_prompt=None, tools=None, tool_choice="auto", **kw):
        if output_cls in self.risposte:
            testo = "\n".join(b.content for b in (input if isinstance(input, list) else [input]) if hasattr(b, "content"))
            self.visti.setdefault(output_cls, []).append(testo)
            valore = self.risposte[output_cls]
            if isinstance(valore, Exception):
                raise valore
            return ClientResponse(content=[StructuredBlock(content=valore)], usage=TokenUsage(prompt_tokens=10, completion_tokens=5))
        return super()._structured_response(input, output_cls, memory, temperature, max_tokens, system_prompt, tools, tool_choice, **kw)
