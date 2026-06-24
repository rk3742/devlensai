"""
Module: Chunking + Vector Indexing.

Splits files into overlapping chunks (preserving some structure awareness
for code: tries to break on blank lines / function boundaries rather than
mid-line) and stores them in a per-repository ChromaDB collection using
our offline embedding function.
"""
import re
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import CHROMA_DIR, settings
from app.services.embeddings import CodeAwareEmbeddingFunction

_EMBED_FN = CodeAwareEmbeddingFunction()
_clients: dict[str, chromadb.ClientAPI] = {}

# Reasonable boundaries to chunk on, in priority order.
_BOUNDARY_RE = re.compile(r"\n(?=\n|def |class |function |export |const |public |private |@)")


def _get_client(repo_id: str) -> chromadb.ClientAPI:
    if repo_id not in _clients:
        path = str(CHROMA_DIR / repo_id)
        _clients[repo_id] = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _clients[repo_id]


def _get_collection(repo_id: str):
    client = _get_client(repo_id)
    return client.get_or_create_collection(
        name="chunks",
        embedding_function=_EMBED_FN,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_text(text: str, rel_path: str) -> list[str]:
    size = settings.chunk_size_chars
    overlap = settings.chunk_overlap_chars

    if len(text) <= size:
        return [text] if text.strip() else []

    # Try to split on logical boundaries first.
    pieces = _BOUNDARY_RE.split(text)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        if len(current) + len(piece) <= size:
            current += piece
        else:
            if current.strip():
                chunks.append(current)
            # If a single piece itself exceeds size, hard-split it with overlap.
            if len(piece) > size:
                start = 0
                while start < len(piece):
                    chunks.append(piece[start:start + size])
                    start += size - overlap
                current = ""
            else:
                current = piece

    if current.strip():
        chunks.append(current)

    if not chunks:
        # Fallback: naive fixed-size split with overlap.
        start = 0
        while start < len(text):
            chunks.append(text[start:start + size])
            start += size - overlap

    return chunks


def index_repository_files(repo_id: str, files_with_content: list[tuple[str, str, str]]) -> int:
    """
    files_with_content: list of (rel_path, language, content)
    Returns total number of chunks indexed.
    """
    collection = _get_collection(repo_id)

    # Reset collection if re-indexing.
    try:
        existing = collection.count()
        if existing > 0:
            client = _get_client(repo_id)
            client.delete_collection("chunks")
            collection = _get_collection(repo_id)
    except Exception:
        pass

    documents, metadatas, ids = [], [], []
    chunk_counter = 0

    for rel_path, language, content in files_with_content:
        chunks = chunk_text(content, rel_path)
        for i, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            documents.append(chunk)
            metadatas.append({
                "file_path": rel_path,
                "language": language,
                "chunk_index": i,
            })
            ids.append(f"{rel_path}::{i}::{chunk_counter}")
            chunk_counter += 1

    # Batch insert (Chroma has a max batch size on some backends; chunk into groups of 200).
    batch_size = 200
    for start in range(0, len(documents), batch_size):
        end = start + batch_size
        collection.add(
            documents=documents[start:end],
            metadatas=metadatas[start:end],
            ids=ids[start:end],
        )

    return chunk_counter


def query_repository(repo_id: str, query: str, top_k: int | None = None) -> list[dict]:
    collection = _get_collection(repo_id)
    n = top_k or settings.top_k_chunks
    count = collection.count()
    if count == 0:
        return []
    n = min(n, count)

    results = collection.query(query_texts=[query], n_results=n)
    output = []
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0] if results.get("distances") else [None] * len(docs)

    for doc, meta, dist in zip(docs, metas, distances):
        output.append({
            "content": doc,
            "file_path": meta.get("file_path"),
            "language": meta.get("language"),
            "chunk_index": meta.get("chunk_index"),
            "distance": dist,
        })
    return output


def delete_repository_index(repo_id: str) -> None:
    try:
        client = _get_client(repo_id)
        client.delete_collection("chunks")
    except Exception:
        pass
    _clients.pop(repo_id, None)
