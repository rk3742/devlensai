"""
Advanced Feature: Repository Comparison.
Advanced Feature: Bug Investigation Assistant.
"""
from app.services.llm_client import call_llm, LLMError
from app.services.indexing import query_repository

COMPARISON_SYSTEM_PROMPT = """You are a senior engineer comparing two versions of a codebase. You're given the file \
lists and category breakdowns of both versions, plus diffed file lists (added/removed/common). Based on this, explain \
in plain English what was likely added, removed, and modified between the two versions. Be concrete about file paths \
and categories. If you can't determine something from the given data, say so rather than guessing."""

BUG_INVESTIGATION_SYSTEM_PROMPT = """You are a senior developer debugging an issue in this codebase. You're given the \
user's description of a bug and relevant code snippets retrieved from the repository. Walk through: (1) which parts \
of the code are most likely involved, (2) what could plausibly be going wrong based on what you see in the code, and \
(3) 2-4 concrete next steps to investigate or fix it. Be specific about file paths and function names from the \
snippets. If the provided code doesn't contain enough information to pinpoint a cause, say so honestly and suggest \
what additional code or logs would help — don't fabricate a root cause."""


def compare_repositories(repo_a_files: list[str], repo_b_files: list[str],
                          repo_a_name: str, repo_b_name: str) -> dict:
    set_a, set_b = set(repo_a_files), set(repo_b_files)
    added = sorted(set_b - set_a)
    removed = sorted(set_a - set_b)
    common = sorted(set_a & set_b)

    summary_text = (
        f"Version 1 ({repo_a_name}): {len(set_a)} files\n"
        f"Version 2 ({repo_b_name}): {len(set_b)} files\n\n"
        f"Added in Version 2 ({len(added)}):\n" + "\n".join(f"  + {p}" for p in added[:60]) + "\n\n"
        f"Removed from Version 1 ({len(removed)}):\n" + "\n".join(f"  - {p}" for p in removed[:60]) + "\n\n"
        f"Present in both ({len(common)} files, possibly modified)"
    )

    try:
        narrative = call_llm(
            messages=[
                {"role": "system", "content": COMPARISON_SYSTEM_PROMPT},
                {"role": "user", "content": summary_text},
            ],
            max_tokens=900,
        )
    except LLMError as e:
        narrative = f"Comparison narrative unavailable: {e}"

    return {
        "added": added,
        "removed": removed,
        "common_count": len(common),
        "narrative": narrative,
    }


def investigate_bug(repo_id: str, bug_description: str) -> dict:
    retrieved = query_repository(repo_id, bug_description, top_k=8)

    if not retrieved:
        return {
            "analysis": "No indexed code was found to investigate. Make sure the repository has finished analyzing.",
            "sources": [],
        }

    context = "\n\n".join(
        f"--- File: {r['file_path']} ---\n{r['content']}" for r in retrieved
    )

    try:
        analysis = call_llm(
            messages=[
                {"role": "system", "content": BUG_INVESTIGATION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Bug description: {bug_description}\n\nRelevant code:\n\n{context}"},
            ],
            max_tokens=1000,
        )
    except LLMError as e:
        return {"analysis": f"Investigation failed: {e}", "sources": [], "error": True}

    sources = [{"file_path": r["file_path"], "snippet": r["content"][:220]} for r in retrieved[:5]]
    return {"analysis": analysis, "sources": sources}
