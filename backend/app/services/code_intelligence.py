"""
Module 3: Code Explainer — explains a single file in plain English.
Module 4: Ask Questions — RAG-based Q&A over the indexed repository.
Module 9: Onboarding Assistant — "what should I learn first" guided path.
"""
from app.services.llm_client import call_llm, call_llm_json, LLMError
from app.services.indexing import query_repository

EXPLAIN_SYSTEM_PROMPT = """You are a senior software engineer explaining code to a teammate who just joined the project. \
Be precise, concrete, and reference actual function/variable names from the code. Never invent functions that aren't in \
the provided code. Respond ONLY with a JSON object with this exact shape:
{
  "summary": "1-3 sentence plain-English summary of what this file does",
  "functions": [{"name": "...", "purpose": "..."}],
  "dependencies": ["list of imports/libraries this file relies on"],
  "notable_patterns": ["short notes on patterns, e.g. 'uses JWT for auth', 'follows MVC controller pattern'"]
}
If the file has no functions (e.g. a config or markdown file), return an empty list for "functions"."""


def explain_file(rel_path: str, language: str, content: str) -> dict:
    user_prompt = f"File: {rel_path}\nLanguage: {language}\n\n```\n{content}\n```"
    try:
        result = call_llm_json(
            messages=[
                {"role": "system", "content": EXPLAIN_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=900,
        )
        result.setdefault("summary", "")
        result.setdefault("functions", [])
        result.setdefault("dependencies", [])
        result.setdefault("notable_patterns", [])
        return result
    except LLMError as e:
        return {
            "summary": f"Explanation unavailable: {e}",
            "functions": [],
            "dependencies": [],
            "notable_patterns": [],
            "error": True,
        }


QA_SYSTEM_PROMPT = """You are DevLens AI, a senior developer who has thoroughly studied this codebase and can answer \
questions about it instantly and precisely. You are given relevant code snippets retrieved from the repository. \
Answer the developer's question using ONLY information present in the provided snippets. If the snippets don't contain \
enough information to answer confidently, say so plainly rather than guessing.

Always cite which file(s) your answer is based on, using the exact file paths given. Be concrete: name actual functions, \
routes, and variables from the snippets rather than speaking generically. Keep the answer focused and skimmable — use \
short paragraphs or a short bullet list, not a wall of text."""


def answer_question(repo_id: str, question: str, chat_history: list[dict] | None = None) -> dict:
    """
    Retrieves relevant chunks via the vector index, then asks the LLM to answer
    using only that retrieved context (classic RAG pattern).
    """
    retrieved = query_repository(repo_id, question, top_k=8)

    if not retrieved:
        return {
            "answer": "I couldn't find any indexed code to search. Make sure the repository has finished analyzing.",
            "sources": [],
        }

    context_blocks = []
    for r in retrieved:
        context_blocks.append(f"--- File: {r['file_path']} (chunk {r['chunk_index']}) ---\n{r['content']}")
    context = "\n\n".join(context_blocks)

    messages = [{"role": "system", "content": QA_SYSTEM_PROMPT}]
    if chat_history:
        for turn in chat_history[-6:]:  # keep recent context bounded
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": f"Relevant code from the repository:\n\n{context}\n\nQuestion: {question}",
    })

    try:
        answer = call_llm(messages, temperature=0.2, max_tokens=900)
    except LLMError as e:
        return {"answer": f"Couldn't generate an answer: {e}", "sources": [], "error": True}

    sources = [
        {"file_path": r["file_path"], "snippet": r["content"][:220]}
        for r in retrieved[:5]
    ]
    return {"answer": answer, "sources": sources}


ONBOARDING_SYSTEM_PROMPT = """You are a senior developer creating an onboarding path for a new engineer joining this \
codebase. Based on the provided structure summary and sample code, suggest a numbered learning order: what to read \
first, second, third, etc., and why. Respond ONLY with a JSON object:
{
  "steps": [{"order": 1, "topic": "...", "reason": "...", "files": ["relevant/file/paths"]}]
}
Limit to 5-7 steps. Be concrete and reference real file paths from what's provided."""


def generate_onboarding_path(structure_summary: dict, sample_context: str) -> dict:
    user_prompt = (
        f"Project structure summary:\n{structure_summary}\n\n"
        f"Sample code from key areas:\n{sample_context}"
    )
    try:
        return call_llm_json(
            messages=[
                {"role": "system", "content": ONBOARDING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=900,
        )
    except LLMError as e:
        return {"steps": [], "error": str(e)}
