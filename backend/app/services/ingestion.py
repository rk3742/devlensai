"""
Module 1: Repository Import.

Handles pulling a repository onto local disk, either by cloning a public
GitHub URL or by extracting an uploaded ZIP archive. Produces a normalized
list of analyzable files ready for chunking.
"""
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import git

from app.config import (
    REPOS_DIR, CODE_EXTENSIONS, IGNORED_DIRS, IGNORED_FILE_PATTERNS, settings,
)


class IngestionError(Exception):
    """Raised for any problem that should be surfaced to the user as a clean message."""
    pass


@dataclass
class AnalyzableFile:
    rel_path: str
    abs_path: Path
    language: str
    size_bytes: int


GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(\.git)?/?$"
)

EXT_TO_LANGUAGE = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript (React)",
    ".ts": "TypeScript", ".tsx": "TypeScript (React)", ".java": "Java",
    ".go": "Go", ".rb": "Ruby", ".php": "PHP", ".c": "C", ".cpp": "C++",
    ".h": "C Header", ".hpp": "C++ Header", ".cs": "C#", ".rs": "Rust",
    ".kt": "Kotlin", ".swift": "Swift", ".scala": "Scala", ".vue": "Vue",
    ".svelte": "Svelte", ".sql": "SQL", ".sh": "Shell", ".yaml": "YAML",
    ".yml": "YAML", ".json": "JSON", ".md": "Markdown", ".html": "HTML",
    ".css": "CSS", ".scss": "SCSS",
}


def validate_github_url(url: str) -> tuple[str, str]:
    """Returns (owner, repo) or raises IngestionError with a clear message."""
    match = GITHUB_URL_RE.match(url.strip())
    if not match:
        raise IngestionError(
            "That doesn't look like a public GitHub repository URL. "
            "Expected something like https://github.com/owner/repo"
        )
    return match.group("owner"), match.group("repo")


def clone_github_repo(url: str, repo_id: str) -> Path:
    owner, repo_name = validate_github_url(url)
    dest = REPOS_DIR / repo_id
    if dest.exists():
        shutil.rmtree(dest)

    try:
        git.Repo.clone_from(url, str(dest), depth=1, single_branch=True)
    except git.GitCommandError as e:
        # Clean up partial clone
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        msg = str(e).lower()
        if "not found" in msg or "repository not found" in msg or "access denied" in msg:
            raise IngestionError(
                f"Couldn't find or access '{owner}/{repo_name}'. "
                "Check that the URL is correct and the repository is public."
            )
        raise IngestionError(
            f"Git failed to clone this repository. It may be private, deleted, or "
            f"the URL may be malformed. Details: {str(e)[:200]}"
        )
    except Exception as e:
        raise IngestionError(f"Unexpected error while cloning repository: {str(e)[:200]}")

    return dest


def extract_zip(zip_path: Path, repo_id: str) -> Path:
    dest = REPOS_DIR / repo_id
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Guard against zip-slip path traversal attacks.
            for member in zf.namelist():
                member_path = (dest / member).resolve()
                if not str(member_path).startswith(str(dest.resolve())):
                    raise IngestionError("ZIP file contains unsafe paths and was rejected.")
            zf.extractall(dest)
    except zipfile.BadZipFile:
        shutil.rmtree(dest, ignore_errors=True)
        raise IngestionError("That file isn't a valid ZIP archive, or it's corrupted.")

    # If the zip contains one single top-level folder, flatten it for consistency.
    entries = list(dest.iterdir())
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest / item.name))
        inner.rmdir()

    return dest


def is_probably_text(path: Path, sniff_bytes: int = 2048) -> bool:
    """Cheap binary-file detector: reject files containing NUL bytes."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(sniff_bytes)
        return b"\x00" not in chunk
    except Exception:
        return False


def walk_repository(repo_path: Path) -> list[AnalyzableFile]:
    """
    Walks the repo, applying ignore rules, extension filters, and size caps.
    Returns a capped, deterministic (sorted) list of files worth analyzing.
    """
    results: list[AnalyzableFile] = []
    total_chars_estimate = 0

    all_paths = sorted(repo_path.rglob("*"))
    for path in all_paths:
        if not path.is_file():
            continue

        # Skip ignored directories anywhere in the path.
        if any(part in IGNORED_DIRS for part in path.parts):
            continue

        name_lower = path.name.lower()
        if any(name_lower.endswith(pat) for pat in IGNORED_FILE_PATTERNS):
            continue

        ext = path.suffix.lower()
        if ext not in CODE_EXTENSIONS:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size == 0 or size > settings.max_file_size_bytes:
            continue

        if not is_probably_text(path):
            continue

        if len(results) >= settings.max_files_per_repo:
            break

        total_chars_estimate += size
        if total_chars_estimate > settings.max_total_chars_indexed:
            break

        rel_path = str(path.relative_to(repo_path)).replace("\\", "/")
        results.append(
            AnalyzableFile(
                rel_path=rel_path,
                abs_path=path,
                language=EXT_TO_LANGUAGE.get(ext, "Other"),
                size_bytes=size,
            )
        )

    return results


def read_file_safely(path: Path, max_chars: int = 60_000) -> str:
    """Reads a file as UTF-8 with replacement, truncating very large files."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_chars + 1)
        if len(content) > max_chars:
            content = content[:max_chars] + "\n\n# [... truncated for length ...]"
        return content
    except Exception as e:
        return f"# Could not read file: {e}"


def cleanup_repo_files(repo_id: str) -> None:
    dest = REPOS_DIR / repo_id
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
