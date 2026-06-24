"""
Local, dependency-light text embedding for code chunks.

Design decision: we deliberately avoid sentence-transformers / fastembed /
chromadb's bundled ONNX downloader. All three pull a model from the network
on first use, which is a real, reproducible failure point in sandboxed,
offline, or flaky-network environments (verified during development: the
default chromadb embedder crashed on a corrupted/blocked model download).

Instead we use a deterministic, code-aware TF-IDF-style hashing vectorizer
that runs entirely offline and installs with zero compiled-model downloads.
For a codebase Q&A tool this trade-off is reasonable: identifier and keyword
overlap (function names, file paths, variable names) is highly predictive
for code retrieval, arguably more so than generic sentence semantics.
"""
import math
import re
from collections import Counter

import numpy as np
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

EMBED_DIM = 512

# Splits camelCase, snake_case, kebab-case, and dotted paths into sub-tokens
# so "getUserData" contributes "get", "user", "data" as well as the whole token.
_TOKEN_SPLIT_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[./\\][\w./\\-]+")


def tokenize_code(text: str) -> list[str]:
    tokens: list[str] = []
    for raw in _WORD_RE.findall(text):
        cleaned = raw.strip("._/\\")
        if not cleaned:
            continue
        tokens.append(cleaned.lower())
        # Sub-tokenize identifiers like camelCase / snake_case for better recall.
        if "_" in cleaned:
            tokens.extend(p.lower() for p in cleaned.split("_") if p)
        else:
            sub = _TOKEN_SPLIT_RE.findall(cleaned)
            if len(sub) > 1:
                tokens.extend(s.lower() for s in sub if s)
    return tokens


def _hash_token(token: str, dim: int) -> int:
    # Stable hash (Python's built-in hash() is salted per-process, unusable here).
    h = 2166136261
    for ch in token:
        h = (h ^ ord(ch)) * 16777619 & 0xFFFFFFFF
    return h % dim


class CodeAwareEmbeddingFunction(EmbeddingFunction):
    """
    Produces a fixed-size vector per document using hashed term frequencies
    with inverse-document-frequency-style down-weighting of overly common
    tokens, L2-normalized so cosine/IP similarity behaves sensibly.
    No network access, no model file, no GPU — pure Python + numpy.
    """

    def __init__(self, dim: int = EMBED_DIM):
        self.dim = dim

    def _embed_one(self, text: str) -> np.ndarray:
        tokens = tokenize_code(text)
        if not tokens:
            return np.zeros(self.dim, dtype=np.float32)

        counts = Counter(tokens)
        vec = np.zeros(self.dim, dtype=np.float32)
        total = len(tokens)
        for tok, count in counts.items():
            idx = _hash_token(tok, self.dim)
            tf = count / total
            # Log-dampen very frequent tokens within the doc (e.g. "self", "the").
            weight = tf * (1.0 + math.log1p(1.0 / (tf + 1e-6)))
            vec[idx] += weight

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def __call__(self, input: Documents) -> Embeddings:
        return [self._embed_one(doc).tolist() for doc in input]


def cosine_sim(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = (np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)
