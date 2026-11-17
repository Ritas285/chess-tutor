"""Bridge datapizza-ai → OpenInference (per Phoenix) — S11 AITHO Junior.

PERCHÉ SERVE
------------
datapizza-ai v0.1.0 emette span OpenTelemetry validi, ma con attributi PROPRI:

    type=agent|generation|tool · model_name · prompt_tokens_used ·
    completion_tokens_used · cached_tokens_used · thinking_tokens_used ·
    input · output · tool_arguments · tool_result · stop_reason

Fa anche una seconda cosa: instrada gli span verso un **progetto** di Phoenix
(`imposta_progetto("Mossa 1 — il pilota")`), riscrivendo la chiave di Resource
`openinference.project.name`. Serve a far sì che la sidebar di Phoenix ripercorra la
struttura della lezione invece di essere un unico calderone.

Phoenix (Arize) legge invece le convenzioni **OpenInference**:

    openinference.span.kind=AGENT|LLM|TOOL · llm.model_name ·
    llm.token_count.prompt · llm.token_count.completion ·
    input.value · output.value · tool.parameters

Senza traduzione gli span ARRIVANO in Phoenix ma si vedono come span generici:
albero e tempi sì, pannelli prompt/risposta e conteggi token no. Questo exporter
li traduce al volo, appena prima dell'invio.

DIDATTICA (S11, ~5 min a schermo — NON si scrive in aula, si legge)
-------------------------------------------------------------------
È il punto in cui la classe capisce la differenza tra:
  - OTel = il TRASPORTO (span, trace, attributi) — standard, e datapizza lo parla;
  - convenzioni semantiche = il CONTRATTO sui nomi — e qui i due parlano dialetti diversi.

USO
---
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from otel_phoenix_bridge import OpenInferenceTranslatingExporter

    # 1) provider NOSTRO (NON DatapizzaMonitoringInstrumentor: quello punta al SaaS Datapizza)
    provider = TracerProvider(resource=Resource.create({"service.name": "aitho-s11"}))

    # 2) exporter verso Phoenix, avvolto nel traduttore
    phoenix = OTLPSpanExporter(endpoint="http://localhost:6006/v1/traces")   # OTLP/HTTP
    provider.add_span_processor(BatchSpanProcessor(OpenInferenceTranslatingExporter(phoenix)))
    trace.set_tracer_provider(provider)

    # 3) OBBLIGATORIO per avere prompt/risposta negli span (default: NON tracciati)
    #    va impostato PRIMA di invocare i client
    import os; os.environ["DATAPIZZA_TRACE_CLIENT_IO"] = "true"

NOTE
----
- Il provider va impostato **una sola volta** e prima delle invocazioni. L'import di
  datapizza può avvenire prima o dopo: `trace.get_tracer(__name__)` a livello di modulo
  restituisce un ProxyTracer che risolve il provider globale in modo lazy. ✅ verificato.
- `tool_result` viene mappato su `output.value`: se in futuro servisse distinguerlo dal
  bridge dell'LLM, usare una chiave dedicata.
- ⚠️ I moduli della `DagPipeline` (embedder, retriever, prompt template, llm) **emettono
  span**, chiamati `PipelineComponent.<Classe>` — ma **privi di attributi**: nome e durata sì,
  niente `type`, niente input/output. Verificato in Phoenix il 4 set 2026. Il bridge assegna
  loro un kind partendo dal nome (`KIND_DA_NOME`), così l'albero è leggibile e compare un nodo
  RETRIEVER; i **chunk** però non ci sono, perché datapizza non li mette da nessuna parte.
- ⚠️ `DATAPIZZA_TRACE_CLIENT_IO` viene letto da datapizza-ai **a ogni chiamata**
  (`os.getenv` dentro lo span, non all'import). Quindi impostarla funziona sempre — ma vale
  solo per le invocazioni SUCCESSIVE: le trace già prodotte non si recuperano. Per questo va
  impostata nella cella di setup, non nella Mossa 3. Sintomo se la si dimentica: in Phoenix
  si vedono gli output dei tool (che non dipendono dalla variabile) ma i pannelli dell'LLM
  sono vuoti.
- Verificato il 3 ago 2026 su datapizza-ai 0.1.0 / datapizza-ai-core 0.1.3 /
  opentelemetry-sdk 1.44.0 / openinference-semantic-conventions.
"""

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

# Chiave di Resource con cui Phoenix raggruppa le trace in PROGETTI.
# Mutabile di proposito: `imposta_progetto()` la cambia a runtime, così la sidebar di
# Phoenix ripercorre la struttura della lezione invece di essere un unico blob.
PROGETTO_KEY = "openinference.project.name"
_PROGETTO = {"nome": "S11 · Lab 11"}


def imposta_progetto(nome: str, provider=None) -> str:
    """Manda gli span SUCCESSIVI a un altro progetto di Phoenix.

    ⚠️ Prima di cambiare etichetta si **svuota il buffer**: il BatchSpanProcessor esporta in
    modo asincrono, quindi senza flush alcuni span della fase precedente partirebbero con il
    nome nuovo. Passate il `provider` per farlo automaticamente.

    Vale solo per notebook e script sequenziali: con richieste concorrenti l'unico modo
    corretto è un `Resource` per provider, oppure l'header `x-project-name` per richiesta.
    """
    if provider is not None and hasattr(provider, "force_flush"):
        provider.force_flush()
    _PROGETTO["nome"] = nome
    return nome

# datapizza `type` → OpenInference span kind
KIND = {
    "agent": "AGENT",
    "generation": "LLM",
    "tool": "TOOL",
}

# I moduli della DagPipeline emettono span chiamati `PipelineComponent.<Classe>` ma
# SENZA NESSUN ATTRIBUTO (verificato in Phoenix il 4 set 2026: "All Attributes: {}").
# Quindi non hanno `type` e finirebbero con kind "unknown", input e output vuoti.
# Non possiamo inventare i contenuti, ma possiamo almeno dare loro il kind giusto
# partendo dal NOME dello span: così in Phoenix l'albero è leggibile e compare un nodo
# RETRIEVER dove ci si aspetta un retrieval.
KIND_DA_NOME = {
    "PipelineComponent.Retriever":              "RETRIEVER",
    "PipelineComponent.OpenAIEmbedder":         "EMBEDDING",
    "PipelineComponent.InferenceClientModule":  "LLM",
    "PipelineComponent.ChatPromptTemplate":     "CHAIN",
}

# attributo datapizza → attributo OpenInference
MAP = {
    "model_name":             "llm.model_name",
    "prompt_tokens_used":     "llm.token_count.prompt",
    "completion_tokens_used": "llm.token_count.completion",
    "cached_tokens_used":     "llm.token_count.prompt_details.cache_read",
    "input":                  "input.value",
    "output":                 "output.value",
    "tool_arguments":         "tool.parameters",
    "tool_result":            "output.value",
}


def translate(attrs: dict, nome: str = "") -> dict:
    """Aggiunge gli attributi OpenInference, conservando quelli datapizza."""
    out = dict(attrs)
    kind = KIND.get(attrs.get("type")) or KIND_DA_NOME.get(nome)
    if kind:
        out["openinference.span.kind"] = kind
    for src, dst in MAP.items():
        if src in attrs:
            out[dst] = attrs[src]
    # Dichiarare il mime type fa mostrare a Phoenix il JSON formattato e navigabile invece
    # di una riga sola. ⚠️ Ma va VERIFICATO, non indovinato dal primo carattere: un testo che
    # comincia con "[system]" non è JSON, e dichiararlo tale lo rende illeggibile — un errore
    # che si vede solo nella UI, non nel codice.
    import json as _json

    for chiave in ("input.value", "output.value"):
        v = out.get(chiave)
        if isinstance(v, str) and v[:1] in ("[", "{"):
            try:
                _json.loads(v)
            except Exception:      # noqa: BLE001
                continue
            out[chiave.replace(".value", ".mime_type")] = "application/json"
    return out


class OpenInferenceTranslatingExporter(SpanExporter):
    """Avvolge un SpanExporter e traduce gli attributi datapizza → OpenInference."""

    def __init__(self, inner: SpanExporter):
        self._inner = inner

    def export(self, spans) -> SpanExportResult:
        # Il progetto sta nel Resource, non negli attributi dello span: qui lo sovrascriviamo
        # per ogni span. L'exporter OTLP raggruppa da sé gli span per Resource, quindi in una
        # sola richiesta possono convivere più progetti.
        etichetta = Resource({PROGETTO_KEY: _PROGETTO["nome"]})
        translated = [
            ReadableSpan(
                name=s.name,
                context=s.context,
                parent=s.parent,
                resource=s.resource.merge(etichetta),
                attributes=translate(dict(s.attributes or {}), s.name or ""),
                events=s.events,
                links=s.links,
                status=s.status,
                kind=s.kind,
                start_time=s.start_time,
                end_time=s.end_time,
                instrumentation_scope=s.instrumentation_scope,
            )
            for s in spans
        ]
        return self._inner.export(translated)

    def shutdown(self) -> None:
        return self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)


# =========================== STRUMENTARE A MANO ==============================
# Il bridge sa TRADURRE ciò che datapizza scrive, ma non può inventare ciò che datapizza
# non scrive — e i moduli della DagPipeline emettono span senza attributi. Quello che
# passa dal NOSTRO codice, però, lo possiamo strumentare bene. Queste due funzioni
# scrivono direttamente le convenzioni OpenInference, senza traduzione.
#
# È anche il contenuto: lo span esiste già: quello che mancava era decidere cosa metterci.

def annota_documenti(span, hits, max_caratteri: int = 2000) -> int:
    """Mette i chunk recuperati su uno span RETRIEVER, in formato OpenInference.

    Phoenix legge `retrieval.documents.{i}.document.{content,id,score,metadata}` e li mostra
    come elenco di documenti navigabile, non come una stringa unica.
    """
    import json

    for i, h in enumerate(hits or []):
        base = f"retrieval.documents.{i}.document"
        testo = getattr(h, "text", None) or str(h)
        span.set_attribute(f"{base}.content", testo[:max_caratteri])
        meta = dict(getattr(h, "metadata", None) or {})
        if meta.get("source_file"):
            span.set_attribute(f"{base}.id", str(meta["source_file"]))
        for campo in ("score", "similarity"):
            v = getattr(h, campo, None)
            if isinstance(v, (int, float)):
                span.set_attribute(f"{base}.score", float(v))
                break
        if meta:
            span.set_attribute(f"{base}.metadata", json.dumps(meta, ensure_ascii=False))
    return len(hits or [])


def span_manuale(nome: str, kind: str, ingresso: str = "", **extra):
    """Context manager per uno span con kind e input già in convenzione OpenInference.

        with span_manuale("retrieval", "RETRIEVER", ingresso=query, **{"retrieval.top_k": k}) as sp:
            hits = ...
            annota_documenti(sp, hits)
    """
    from contextlib import contextmanager

    from opentelemetry import trace

    @contextmanager
    def _cm():
        tracer = trace.get_tracer("aitho.s11")
        with tracer.start_as_current_span(nome) as sp:
            sp.set_attribute("openinference.span.kind", kind)
            if ingresso:
                sp.set_attribute("input.value", ingresso)
            for chiave, valore in extra.items():
                if valore is not None:
                    sp.set_attribute(chiave, valore)
            yield sp

    return _cm()


def client_tracciato(client, model_name: str = ""):
    """Avvolge `client.invoke` in uno span LLM con prompt, risposta e token.

    PERCHÉ NON BASTA `DATAPIZZA_TRACE_CLIENT_IO`
    --------------------------------------------
    datapizza-ai scriverebbe input e output sullo span `client.invoke`, ma solo se quella
    variabile è "true" **nel momento della chiamata** — e i token li scrive comunque. Il
    risultato, quando qualcosa va storto nell'ordine, è uno span con i numeri e senza il
    contenuto: un sintomo che sembra un problema del tracing e invece è un problema di
    configurazione. Verificato sul campo il 4 set 2026: la variabile risultava impostata e
    gli attributi non comparivano.

    Qui l'informazione non dipende più da una variabile d'ambiente: la scriviamo noi, attorno
    alla chiamata. Costa uno span in più (il nostro, con il contenuto; quello di datapizza
    resta come figlio, con i token) e in cambio è deterministico.

    Nel percorso dell'AGENTE questo è l'unico modo: là non c'è nessun modulo di pipeline da
    arricchire, `client.invoke` è l'unico span LLM che esiste.

        client = bridge.client_tracciato(OpenAIClient(...), model_name="gpt-4o-mini")
        agente = Agent(name="rag_agent", client=client, tools=[rag_tool], ...)
    """
    try:
        _originale = client.invoke
    except AttributeError:
        print("⚠️  client senza `invoke`: non tracciato")
        return client

    def invoke(*args, **kwargs):
        testo_in = kwargs.get("input")
        if testo_in is None and args:
            testo_in = args[0]
        with span_manuale("llm", "LLM") as sp:
            try:
                if model_name:
                    sp.set_attribute("llm.model_name", model_name)
                # Ciò che il modello RICEVE: system + contesto + domanda, come elenco di
                # messaggi. Non la sola domanda: quella da sola nasconde il contesto.
                assemblato = annota_messaggi(
                    sp, system_prompt=kwargs.get("system_prompt"),
                    memory=kwargs.get("memory"), domanda=testo_in)
                if assemblato:
                    sp.set_attribute("input.value", assemblato)
                if testo_in:
                    sp.set_attribute("llm.domanda_utente", str(testo_in))
            except Exception:      # noqa: BLE001
                pass

            risposta = _originale(*args, **kwargs)

            try:
                annota_risposta(sp, getattr(risposta, "text", None) or "")
                chiamate = getattr(risposta, "function_calls", None)
                if chiamate:
                    sp.set_attribute("llm.tool_calls_count", len(chiamate))
                for attr, chiave in (("prompt_tokens_used", "llm.token_count.prompt"),
                                     ("completion_tokens_used", "llm.token_count.completion")):
                    v = getattr(risposta, attr, None)
                    if isinstance(v, int):
                        sp.set_attribute(chiave, v)
            except Exception:      # noqa: BLE001
                pass
            return risposta

    client.invoke = invoke
    return client


def annota_messaggi(sp, system_prompt=None, memory=None, domanda=None,
                    max_caratteri: int = 8000) -> str:
    """Scrive ciò che il modello RICEVE DAVVERO, in convenzione OpenInference.

    IL PUNTO
    --------
    Mettere la domanda grezza in `input.value` è fuorviante: il modello non riceve la domanda,
    riceve **system prompt + contesto assemblato dal prompt template + domanda**. Se in Phoenix
    si legge solo la domanda, manca precisamente l'informazione per cui si apre Phoenix — cioè
    *cosa ha letto il modello prima di rispondere*.

    Phoenix legge `llm.input_messages.{i}.message.{role,content}` e li mostra come **elenco di
    messaggi** con i ruoli, non come una stringa unica. Ritorna anche il testo assemblato, da
    usare per `input.value` così la colonna in tabella dice qualcosa di vero.
    """
    import json

    messaggi = []
    if system_prompt:
        messaggi.append(("system", str(system_prompt)))

    turni = None
    if memory is not None:
        try:
            grezzo = memory.json_dumps() if hasattr(memory, "json_dumps") else str(memory)
            turni = json.loads(grezzo)
        except Exception:          # noqa: BLE001
            turni = None

    def _testo(contenuto):
        if isinstance(contenuto, list):
            pezzi = []
            for b in contenuto:
                if isinstance(b, dict):
                    pezzi.append(str(b.get("content") or b.get("text") or b))
                else:
                    pezzi.append(str(b))
            return "\n".join(pezzi)
        return str(contenuto)

    if isinstance(turni, list) and turni:
        for t in turni:
            if isinstance(t, dict):
                messaggi.append((str(t.get("role") or "user").lower(),
                                 _testo(t.get("content", t))))
            else:
                messaggi.append(("user", str(t)))
    elif domanda:
        messaggi.append(("user", str(domanda)))

    for i, (ruolo, contenuto) in enumerate(messaggi):
        sp.set_attribute(f"llm.input_messages.{i}.message.role", ruolo)
        sp.set_attribute(f"llm.input_messages.{i}.message.content", contenuto[:max_caratteri])

    assemblato = "\n\n".join(f"[{r}]\n{c}" for r, c in messaggi)
    return assemblato[:max_caratteri]


def annota_risposta(sp, testo: str, max_caratteri: int = 8000) -> None:
    """La risposta come messaggio assistant, così Phoenix la accoppia all'input."""
    if not testo:
        return
    sp.set_attribute("output.value", testo[:max_caratteri])
    sp.set_attribute("llm.output_messages.0.message.role", "assistant")
    sp.set_attribute("llm.output_messages.0.message.content", testo[:max_caratteri])
