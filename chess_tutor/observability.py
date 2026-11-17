"""Osservabilità (traccia D, lezione S11): due livelli, entrambi OPZIONALI (se non sono attivi il tutor funziona uguale).

  Trace -> Phoenix: cosa è successo in QUESTA domanda: albero agente / modello / strumento, prompt, documenti recuperati, token.
           "Perché questa risposta è sbagliata?"
  Metriche -> Prometheus + Grafana: quanto costa e quanto è lento IN GENERALE: domande, latenza p50/p95, token, costo.
           "Quanto spendo? Quante volte intervengono i guardrail?"

Le due cose rispondono a domande diverse e non si sostituiscono (S11). Etichette delle metriche a BASSA cardinalità (ramo, esito,
strumento): mai il testo delle domande.
"""
from __future__ import annotations

import os

PHOENIX_HTTP = "http://localhost:6006/v1/traces"     # OTLP su HTTP, NON la porta 4317 (gRPC): sbagliare non dà errori, dà zero trace
_stato = {"tracing": False, "provider": None}


def setup_tracing(endpoint: str | None = None, progetto: str = "Chess Tutor") -> bool:
    """Manda gli span di datapizza-ai a Phoenix. Si attiva con PHOENIX_ENDPOINT (o passando `endpoint`); da chiamare UNA volta,
    prima delle domande. Ritorna True se il tracing è attivo."""
    endpoint = endpoint or os.getenv("PHOENIX_ENDPOINT", "")
    if not endpoint or _stato["tracing"]:
        return _stato["tracing"]
    # OBBLIGATORIO (S11): senza questa variabile, negli span non ci sono prompt e risposte. Va impostata PRIMA di ogni chiamata.
    os.environ["DATAPIZZA_TRACE_CLIENT_IO"] = "true"

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    from .otel_phoenix_bridge import OpenInferenceTranslatingExporter, imposta_progetto

    # Il ponte traduce gli attributi di datapizza (prompt_tokens_used…) in quelli che Phoenix capisce (OpenInference).
    processore = BatchSpanProcessor(OpenInferenceTranslatingExporter(OTLPSpanExporter(endpoint=endpoint)))
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):          # S11: se un provider c'è già ci si AGGANCIA (il provider è "set-once")
        provider.add_span_processor(processore)
    else:
        provider = TracerProvider(resource=Resource.create({"service.name": "chess-tutor"}))
        provider.add_span_processor(processore)
        trace.set_tracer_provider(provider)
    imposta_progetto(progetto, provider)
    _stato.update(tracing=True, provider=provider)
    return True


def svuota_tracing() -> None:
    """Invia subito gli span rimasti in coda. Serve nei programmi che finiscono presto: l'invio è asincrono e, senza questo,
    gli ultimi span andrebbero persi."""
    provider = _stato["provider"]
    if provider is not None and hasattr(provider, "force_flush"):
        provider.force_flush()


def _tipo_intervento(nota: str) -> str:
    """"link esterno rimosso (collector.example)" -> "link_esterno_rimosso": etichetta stabile, senza dettagli variabili."""
    return nota.split(" (")[0].strip().replace(" ", "_")


class Metriche:
    """Metriche Prometheus. `registra(risposta)` viene chiamato dal Tutor dopo ogni domanda.
    Con `porta` espone http://localhost:<porta>/metrics (Prometheus la legge da lì); senza porta resta in memoria (per i test)."""

    def __init__(self, porta: int | None = None, indirizzo: str = "0.0.0.0"):
        """`indirizzo="0.0.0.0"` = tutte le interfacce IPv4: serve a Prometheus nel container Docker, che raggiunge il PC da
        host.docker.internal e non da 127.0.0.1. (Con l'indirizzo vuoto "" il server si metteva in ascolto solo su IPv6 e il
        container riceveva "connection refused": misurato.) Windows può chiedere una volta se consentire l'accesso di rete."""
        from prometheus_client import CollectorRegistry, Counter, Histogram, start_http_server

        self.registry = CollectorRegistry()           # un registro proprio: si possono creare più istanze (test) senza conflitti
        # La libreria aggiunge da sola "_total" ai contatori: chess_domande diventa chess_domande_total
        self.domande = Counter("chess_domande", "Domande ricevute", ["ramo", "esito"], registry=self.registry)
        # Bucket scelti a mano: il p95 si ricostruisce da questi, e se sono sbagliati il percentile è inutile (S11)
        self.latenza = Histogram("chess_latenza_secondi", "Tempo per rispondere", registry=self.registry,
                                 buckets=(0.5, 1, 2, 3, 5, 8, 13, 21, 34))
        self.token = Counter("chess_token", "Token usati", ["tipo"], registry=self.registry)
        self.costo = Counter("chess_costo_usd", "Costo stimato in dollari", registry=self.registry)
        self.strumenti = Counter("chess_chiamate_strumento", "Chiamate per strumento", ["strumento"], registry=self.registry)
        self.interventi = Counter("chess_interventi_guardrail", "Interventi dei guardrail", ["tipo"], registry=self.registry)
        if porta:
            start_http_server(porta, addr=indirizzo, registry=self.registry)

    def registra(self, r) -> None:
        esito = "bloccata" if r.bloccata else "fuori_tema" if r.fuori_tema else "risposta"
        for ramo in r.rami or ["nessuno"]:
            self.domande.labels(ramo=ramo, esito=esito).inc()
        self.latenza.observe(r.latenza_s)
        self.token.labels(tipo="prompt").inc(r.token_prompt)
        self.token.labels(tipo="completati").inc(r.token_completati)
        self.costo.inc(r.costo_usd)
        for nome in r.tool_usati:
            self.strumenti.labels(strumento=nome).inc()
        if r.bloccata:                                   # il guardrail di input conta come un intervento
            self.interventi.labels(tipo="domanda_bloccata").inc()
        for nota in r.note:
            self.interventi.labels(tipo=_tipo_intervento(nota)).inc()

    def valore(self, nome: str, **etichette) -> float:
        """Utile ai test: il valore attuale di una metrica."""
        return self.registry.get_sample_value(nome, etichette or None) or 0.0


def attiva_da_ambiente() -> "Metriche | None":
    """Tracing se c'è PHOENIX_ENDPOINT; metriche se c'è ENABLE_METRICS (porta in METRICS_PORT, default 8000)."""
    setup_tracing()
    if os.getenv("ENABLE_METRICS"):
        return Metriche(int(os.getenv("METRICS_PORT", "8000")))
    return None
