"""
Module 2: Project Structure Analyzer.

Builds a navigable tree of the repository and classifies top-level areas
(frontend/backend/database/config/etc.) using path heuristics — fast,
deterministic, and doesn't burn any LLM quota for something a few regexes
can do reliably.
"""
import re
from collections import defaultdict
from pathlib import Path

from app.services.ingestion import AnalyzableFile

CATEGORY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Frontend", re.compile(r"(^|/)(src/(components|pages|views|screens)|frontend|client|public)(/|$)", re.I)),
    ("Backend", re.compile(r"(^|/)(routes|controllers|api|server|backend|handlers)(/|$)", re.I)),
    ("Database", re.compile(r"(^|/)(models|migrations|schema|prisma|database|db)(/|$)", re.I)),
    ("Services", re.compile(r"(^|/)(services|lib|utils|helpers)(/|$)", re.I)),
    ("Tests", re.compile(r"(^|/)(tests?|__tests__|spec)(/|$)", re.I)),
    ("Config", re.compile(r"(^|/)(config|\.github|docker)(/|$)|^(\.env|docker-compose|dockerfile)", re.I)),
    ("Documentation", re.compile(r"(^|/)(docs?)(/|$)|\.md$", re.I)),
]


def categorize_file(rel_path: str) -> str:
    for category, pattern in CATEGORY_PATTERNS:
        if pattern.search(rel_path):
            return category
    return "Other"


def build_tree(files: list[AnalyzableFile]) -> dict:
    """Builds a nested dict representing the folder/file tree."""
    tree: dict = {}
    for f in files:
        parts = f.rel_path.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {"__type__": "dir", "__children__": {}})["__children__"]
        node[parts[-1]] = {
            "__type__": "file",
            "language": f.language,
            "size_bytes": f.size_bytes,
        }
    return tree


def summarize_structure(files: list[AnalyzableFile]) -> dict:
    """
    Returns a high-level summary: category breakdown, language breakdown,
    and the full tree, used by the Project Structure Analyzer module.
    """
    category_counts: dict[str, int] = defaultdict(int)
    language_counts: dict[str, int] = defaultdict(int)
    category_files: dict[str, list[str]] = defaultdict(list)

    for f in files:
        cat = categorize_file(f.rel_path)
        category_counts[cat] += 1
        language_counts[f.language] += 1
        if len(category_files[cat]) < 30:
            category_files[cat].append(f.rel_path)

    tree = build_tree(files)

    return {
        "total_files": len(files),
        "categories": dict(sorted(category_counts.items(), key=lambda x: -x[1])),
        "languages": dict(sorted(language_counts.items(), key=lambda x: -x[1])),
        "category_files": dict(category_files),
        "tree": tree,
    }
