"""
Central configuration for DevLens AI backend.
All tunable values live here so behavior can be changed without touching
business logic, and so the README can document exactly what is configurable.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
REPOS_DIR = STORAGE_DIR / "repos"
CHROMA_DIR = STORAGE_DIR / "chroma"
DB_PATH = STORAGE_DIR / "devlens.db"

for d in (STORAGE_DIR, REPOS_DIR, CHROMA_DIR):
    d.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    # --- AI provider ---
    # "groq" uses Groq's free-tier cloud API (fast, recommended default).
    # "ollama" uses a locally running Ollama instance (fully offline, no API key).
    ai_provider: str = os.environ.get("AI_PROVIDER", "groq")

    groq_api_key: str = os.environ.get("GROQ_API_KEY", "")
    groq_model: str = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    ollama_base_url: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    ollama_model: str = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:7b")

    # --- Ingestion limits (protect against giant repos blowing up memory/time) ---
    max_file_size_bytes: int = 400_000          # skip files bigger than this
    max_files_per_repo: int = 4000              # hard cap on files analyzed
    max_total_chars_indexed: int = 15_000_000   # hard cap on indexed content
    chunk_size_chars: int = 1800
    chunk_overlap_chars: int = 200

    # --- Retrieval ---
    top_k_chunks: int = 8

    # --- CORS ---
    # Comma-separated list of allowed origins. Defaults to local dev.
    # In production, set CORS_ORIGINS to your deployed frontend URL, e.g.
    # CORS_ORIGINS=https://devlens-ai.vercel.app
    cors_origins_raw: str = os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins_raw.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

# File extensions DevLens AI knows how to meaningfully analyze.
CODE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rb", ".php",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".rs", ".kt", ".swift", ".scala",
    ".vue", ".svelte", ".sql", ".sh", ".yaml", ".yml", ".json", ".md",
    ".html", ".css", ".scss",
}

# Directories that are never useful to analyze.
IGNORED_DIRS = {
    "node_modules", ".git", "__pycache__", "venv", ".venv", "env",
    "dist", "build", ".next", ".nuxt", "coverage", ".pytest_cache",
    "target", "vendor", ".idea", ".vscode", "bin", "obj", "out",
    ".cache", "egg-info", ".tox", "site-packages",
}

IGNORED_FILE_PATTERNS = (
    ".min.js", ".min.css", "-lock.json", ".lock", ".map", ".woff",
    ".woff2", ".ttf", ".eot", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ico", ".pdf", ".zip", ".tar", ".gz", ".mp4", ".mp3", ".db",
    ".sqlite", ".sqlite3", ".bin", ".exe", ".dll", ".so", ".dylib",
)
