"""
SQLite persistence layer. We use raw sqlite3 (stdlib) rather than an ORM
to keep the dependency surface minimal and avoid version-mismatch risk
between an ORM, its driver, and the SQLite version on the user's machine.
"""
import sqlite3
import json
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from app.config import DB_PATH


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,      -- 'github' | 'zip'
                source_url TEXT,
                local_path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',  -- pending|analyzing|ready|failed
                error_message TEXT,
                file_count INTEGER DEFAULT 0,
                total_chunks INTEGER DEFAULT 0,
                languages TEXT,                  -- JSON list
                structure_json TEXT,             -- JSON tree
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                rel_path TEXT NOT NULL,
                language TEXT,
                size_bytes INTEGER,
                line_count INTEGER,
                explanation_json TEXT,           -- cached AI explanation
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                role TEXT NOT NULL,              -- 'user' | 'assistant'
                content TEXT NOT NULL,
                sources_json TEXT,                -- JSON list of {file, snippet}
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS findings (
                id TEXT PRIMARY KEY,
                repo_id TEXT NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,              -- 'dead_code' | 'tech_debt'
                file_path TEXT,
                title TEXT NOT NULL,
                detail TEXT,
                confidence INTEGER,
                severity TEXT,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_files_repo ON files(repo_id);
            CREATE INDEX IF NOT EXISTS idx_chat_repo ON chat_messages(repo_id);
            CREATE INDEX IF NOT EXISTS idx_findings_repo ON findings(repo_id);
            """
        )


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def now() -> float:
    return time.time()


# ---------- Repositories ----------

def create_repository(name: str, source_type: str, source_url: Optional[str], local_path: str) -> str:
    repo_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO repositories (id, name, source_type, source_url, local_path, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (repo_id, name, source_type, source_url, local_path, now()),
        )
    return repo_id


def update_repository(repo_id: str, **fields: Any) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values())
    with get_conn() as conn:
        conn.execute(f"UPDATE repositories SET {cols} WHERE id = ?", (*values, repo_id))


def get_repository(repo_id: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,)).fetchone()
        return _row_to_dict(row) if row else None


def list_repositories() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM repositories ORDER BY created_at DESC").fetchall()
        return [_row_to_dict(r) for r in rows]


def delete_repository(repo_id: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))


# ---------- Files ----------

def insert_file(repo_id: str, rel_path: str, language: str, size_bytes: int, line_count: int) -> str:
    file_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO files (id, repo_id, rel_path, language, size_bytes, line_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (file_id, repo_id, rel_path, language, size_bytes, line_count, now()),
        )
    return file_id


def bulk_insert_files(repo_id: str, files: list[dict]) -> None:
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO files (id, repo_id, rel_path, language, size_bytes, line_count, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (new_id(), repo_id, f["rel_path"], f["language"], f["size_bytes"], f["line_count"], now())
                for f in files
            ],
        )


def get_file_by_path(repo_id: str, rel_path: str) -> Optional[dict]:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM files WHERE repo_id = ? AND rel_path = ?", (repo_id, rel_path)
        ).fetchone()
        return _row_to_dict(row) if row else None


def list_files(repo_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM files WHERE repo_id = ? ORDER BY rel_path", (repo_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]


def cache_file_explanation(repo_id: str, rel_path: str, explanation: dict) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE files SET explanation_json = ? WHERE repo_id = ? AND rel_path = ?",
            (json.dumps(explanation), repo_id, rel_path),
        )


# ---------- Chat ----------

def insert_chat_message(repo_id: str, role: str, content: str, sources: Optional[list] = None) -> str:
    msg_id = new_id()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, repo_id, role, content, sources_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (msg_id, repo_id, role, content, json.dumps(sources or []), now()),
        )
    return msg_id


def list_chat_messages(repo_id: str) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE repo_id = ? ORDER BY created_at", (repo_id,)
        ).fetchall()
        result = []
        for r in rows:
            d = _row_to_dict(r)
            d["sources"] = json.loads(d.pop("sources_json") or "[]")
            result.append(d)
        return result


# ---------- Findings ----------

def bulk_insert_findings(repo_id: str, findings: list[dict]) -> None:
    with get_conn() as conn:
        conn.executemany(
            "INSERT INTO findings (id, repo_id, kind, file_path, title, detail, confidence, severity, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    new_id(), repo_id, f["kind"], f.get("file_path"), f["title"],
                    f.get("detail", ""), f.get("confidence", 50), f.get("severity", "medium"), now(),
                )
                for f in findings
            ],
        )


def list_findings(repo_id: str, kind: Optional[str] = None) -> list[dict]:
    with get_conn() as conn:
        if kind:
            rows = conn.execute(
                "SELECT * FROM findings WHERE repo_id = ? AND kind = ? ORDER BY confidence DESC",
                (repo_id, kind),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM findings WHERE repo_id = ? ORDER BY kind, confidence DESC", (repo_id,)
            ).fetchall()
        return [_row_to_dict(r) for r in rows]


def clear_findings(repo_id: str, kind: Optional[str] = None) -> None:
    with get_conn() as conn:
        if kind:
            conn.execute("DELETE FROM findings WHERE repo_id = ? AND kind = ?", (repo_id, kind))
        else:
            conn.execute("DELETE FROM findings WHERE repo_id = ?", (repo_id,))
