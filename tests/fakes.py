"""Embedder finto per i test: nessuna chiave, nessuna rete."""
import hashlib
import math

from datapizza.core.embedder import BaseEmbedder

from chess_tutor import config


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
