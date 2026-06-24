"""
Module 5: Documentation Generator.

Generates README.md, API documentation, and an installation/developer guide
using the structure summary plus a curated sample of real file contents,
so the output is grounded in what's actually in the repo rather than
generic boilerplate.
"""
from app.services.llm_client import call_llm, LLMError

README_SYSTEM_PROMPT = """You are a senior developer writing documentation for a codebase you have fully studied. \
Generate a clear, professional README.md in Markdown. Base every claim on the provided structure summary and code \
samples — never invent features, scripts, or dependencies that aren't evidenced in what you were given. If you're \
unsure about an exact run command, phrase it as a sensible convention for the detected stack rather than stating it \
as fact. Include these sections where applicable: Overview, Tech Stack, Project Structure, Installation, \
Running the Project, Key Features. Keep it concise and skimmable — this is for a developer who needs to get oriented \
fast, not a marketing page."""

API_DOC_SYSTEM_PROMPT = """You are documenting the API surface of a codebase. Based on the provided code (route \
definitions, controller functions, etc.), produce Markdown API documentation listing each endpoint or public function \
you can identify: method, path (if it's an HTTP route), parameters, and a one-line description. Only document \
things actually visible in the provided code. If no API routes are evident, say so plainly rather than inventing any."""

INSTALL_GUIDE_SYSTEM_PROMPT = """You are writing a step-by-step installation and developer setup guide for this \
codebase, based on its detected stack and structure. Produce numbered Markdown steps covering: cloning, installing \
dependencies, environment variables (if any config/.env patterns are evident), and running the project. Keep each \
step short and concrete. Don't invent exact package names you weren't shown — describe the general step \
(e.g. "Install backend dependencies") if specifics aren't visible."""


def _build_context(structure_summary: dict, sample_files: list[tuple[str, str]]) -> str:
    cat_lines = "\n".join(f"- {cat}: {count} files" for cat, count in structure_summary["categories"].items())
    lang_lines = "\n".join(f"- {lang}: {count} files" for lang, count in structure_summary["languages"].items())

    sample_blocks = []
    for path, content in sample_files[:12]:
        truncated = content[:1500]
        sample_blocks.append(f"--- {path} ---\n{truncated}")

    return (
        f"Total files analyzed: {structure_summary['total_files']}\n\n"
        f"Categories:\n{cat_lines}\n\n"
        f"Languages:\n{lang_lines}\n\n"
        f"Sample files:\n\n" + "\n\n".join(sample_blocks)
    )


def generate_readme(structure_summary: dict, sample_files: list[tuple[str, str]], repo_name: str) -> str:
    context = _build_context(structure_summary, sample_files)
    try:
        return call_llm(
            messages=[
                {"role": "system", "content": README_SYSTEM_PROMPT},
                {"role": "user", "content": f"Repository name: {repo_name}\n\n{context}"},
            ],
            max_tokens=1800,
        )
    except LLMError as e:
        return f"# {repo_name}\n\n_Documentation generation failed: {e}_"


def generate_api_docs(sample_files: list[tuple[str, str]]) -> str:
    relevant = [
        (p, c) for p, c in sample_files
        if any(k in p.lower() for k in ("route", "controller", "api", "view", "handler", "endpoint"))
    ] or sample_files[:8]

    context = "\n\n".join(f"--- {p} ---\n{c[:2000]}" for p, c in relevant[:10])
    try:
        return call_llm(
            messages=[
                {"role": "system", "content": API_DOC_SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            max_tokens=1500,
        )
    except LLMError as e:
        return f"_API documentation generation failed: {e}_"


def generate_install_guide(structure_summary: dict, sample_files: list[tuple[str, str]]) -> str:
    context = _build_context(structure_summary, sample_files[:6])
    try:
        return call_llm(
            messages=[
                {"role": "system", "content": INSTALL_GUIDE_SYSTEM_PROMPT},
                {"role": "user", "content": context},
            ],
            max_tokens=900,
        )
    except LLMError as e:
        return f"_Installation guide generation failed: {e}_"
