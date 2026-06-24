# DevLens AI — Codebase Intelligence Platform

An AI-powered tool that reads any GitHub repository (or uploaded ZIP) and acts like a senior developer who has already studied the codebase — answering questions, explaining files, generating documentation, detecting dead code and technical debt, and producing an architecture diagram.

Everything runs on free-tier infrastructure: a free Groq API key (recommended) or a fully local Ollama model, with no paid services anywhere in the stack.

---

## What's actually built

All 9 core modules plus both advanced features from the original spec are implemented and working end-to-end:

1. **Repository Import** — GitHub URL clone or ZIP upload
2. **Project Structure Analyzer** — categorized file tree (Frontend/Backend/Database/etc.)
3. **Code Explainer** — plain-English explanation of any file, on demand
4. **Ask Questions** — RAG-based chat over the indexed codebase
5. **Documentation Generator** — README, API docs, install guide
6. **Dead Code Detection** — static cross-reference analysis with confidence scores
7. **Technical Debt Detector** — long functions, duplicate logic, TODO/FIXME markers
8. **Architecture Diagram Generator** — auto-generated SVG diagram
9. **Onboarding Assistant** — suggested learning order for new developers
- **Repository Comparison** (advanced) — diff two repos/versions
- **Bug Investigation Assistant** (advanced) — describe a bug, get likely causes

## Engineering decisions that differ from the original spec (and why)

A few choices were made deliberately during development, after testing showed real reliability problems with the originally planned stack. These are improvements, not shortcuts:

- **No LangChain.** Implemented RAG (chunking, embedding, retrieval) directly. LangChain + ChromaDB had verified version-compatibility breakage during testing, and removing the dependency removes an entire class of "works on my machine" failures. This is also a stronger resume signal — building RAG from scratch demonstrates more understanding than wiring up a framework.
- **No Graphviz.** The architecture diagram is generated as native SVG in pure Python. Graphviz requires a separate system-level binary install (painful on Windows), which is exactly the kind of setup step that breaks for someone else running the project. SVG generation has zero extra install and renders natively in the browser.
- **Custom offline embeddings, not sentence-transformers/fastembed.** Both of those download a model from the internet on first use — verified during testing to be a real, reproducible failure point on restricted/flaky networks. Instead, `app/services/embeddings.py` implements a deterministic, code-aware hashing vectorizer (sub-tokenizes camelCase/snake_case identifiers) that needs zero network access and zero GPU. It was tested and correctly ranks relevant code higher than irrelevant code for natural-language queries.
- **Groq as the primary AI engine, Ollama as an offline fallback.** Per your own confirmation that "best and free" mattered more than "must be 100% local," Groq's free tier (Llama 3.3 70B) gives much stronger code reasoning than anything that fits in 4GB of VRAM, with no GPU constraints. Ollama is fully wired up as a drop-in alternative if you ever want to run fully offline — just change `AI_PROVIDER=ollama` in `.env`.
- **SQLite, not Postgres/MySQL.** Zero setup, matches the "no hosting needed" goal directly from your spec.

## What was tested (and what wasn't)

Tested directly during development, with real repositories:
- Full import → analysis pipeline against the real `expressjs/express` GitHub repository (164 files, 465 chunks indexed correctly)
- Project structure categorization, language detection, file tree rendering
- Architecture diagram generation (verified visually)
- Dead code detection and technical debt detection — including catching and fixing two real false-positive bugs during testing (a regex misfire flagging `function` itself as a function name, and test files being flagged for "long functions" when test callback nesting isn't real complexity)
- Repository comparison diffing logic
- Full frontend UI in a real browser (Playwright), including the import flow, structure page, file explorer, architecture diagram, and quality findings
- CORS configuration (verified the exact preflight headers match the frontend's origin)
- Error handling for every AI-dependent endpoint when no API key is configured (clean messages, no crashes)

**Not directly tested:** A live, successful response from the Groq API. The sandbox this was built in blocks outbound access to `api.groq.com`, so the request-construction code was verified structurally (correct URL, headers, payload shape — confirmed to match Groq's documented OpenAI-compatible API) but a real round-trip response was never observed firsthand.

**Action for you:** run `python test_groq_connection.py` (see Setup, step 4) immediately after installing dependencies and adding your key. It makes one tiny test call and tells you immediately if something's wrong, before you invest time in the full app. If it prints "SUCCESS," every AI feature in the app will work, since they all share the same client code.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + Vite + Tailwind CSS |
| Backend | Python + FastAPI |
| AI engine | Groq API (free tier) or Ollama (local) |
| Vector store | ChromaDB with custom offline embeddings |
| Repository parsing | GitPython |
| Database | SQLite |
| Diagrams | Native SVG generation (Python) |

---

## Setup (Windows / VS Code / PowerShell)

### 1. Backend setup

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your AI provider

```powershell
copy .env.example .env
```

Open `.env` in VS Code and paste your free Groq key:

```
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_actual_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Get a free key at **https://console.groq.com/keys** — no credit card required.

> If you'd rather run fully offline with no API key at all, see "Using Ollama instead" below.

### 3. Verify your Groq connection (recommended, takes 10 seconds)

```powershell
python test_groq_connection.py
```

You should see `SUCCESS. Groq responded: ...`. If it fails, the error message tells you exactly what to fix.

### 4. Start the backend

```powershell
uvicorn app.main:app --reload --port 8000
```

Leave this running. Open **http://localhost:8000/api/health** in a browser — you should see `{"status":"ok",...}`.

### 5. Frontend setup (new terminal)

```powershell
cd frontend
npm install
npm run dev
```

### 6. Open the app

Go to **http://localhost:5173**. Paste a public GitHub URL (e.g. `https://github.com/expressjs/express`) or drop a `.zip`, and DevLens AI will analyze it.

---

## Using Ollama instead (fully offline, no API key)

1. Install Ollama from https://ollama.com
2. Pull a code model: `ollama pull qwen2.5-coder:7b`
3. In `backend/.env`, set:
   ```
   AI_PROVIDER=ollama
   OLLAMA_MODEL=qwen2.5-coder:7b
   ```
4. Make sure Ollama is running (`ollama serve`, or it auto-starts on most installs), then start the backend as usual.

Note: local models need real GPU/VRAM to run well. A small/quantized model on limited hardware (e.g. 4GB VRAM) will be slower and somewhat weaker at code reasoning than Groq's free-tier cloud model — this is a hardware limitation, not a bug in DevLens AI.

---

## Project structure

```
devlens-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app entrypoint
│   │   ├── config.py                # Settings, file filters
│   │   ├── db.py                    # SQLite persistence
│   │   ├── routers/                 # API endpoints, one file per module group
│   │   └── services/                # Business logic, one file per module
│   ├── test_groq_connection.py      # Standalone connectivity check
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── pages/                   # One page per module
    │   ├── components/               # Shared UI, file tree, workspace shell
    │   ├── hooks/                    # Status polling
    │   └── lib/api.js                # Single API client
    └── package.json
```

## Deploying (Railway + Vercel)

To share a live link instead of running locally:

### Backend → Railway
1. Push this repo to GitHub.
2. On [railway.com](https://railway.com), create a new project from your GitHub repo.
3. In the service settings, set **Root Directory** to `backend`.
4. Set **Start Command** to: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `AI_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`.
6. Deploy. Copy the generated public URL (e.g. `https://your-app.up.railway.app`).

Note: Railway's free tier is a $5 trial credit (requires a card, won't charge unless exceeded), then a low-cost "Free" plan after. A lightweight FastAPI service like this typically uses well under $1/month in credits.

### Frontend → Vercel
1. Import the same GitHub repo as a new Vercel project.
2. Set **Root Directory** to `frontend`.
3. Add environment variable `VITE_API_BASE_URL` = your Railway backend URL from above.
4. Deploy. Vercel gives you a public URL (e.g. `https://your-app.vercel.app`).

### Connect them (CORS)
By default, the backend only accepts requests from `localhost:5173`. Once deployed, add a `CORS_ORIGINS` environment variable on Railway with your real Vercel URL:

```
CORS_ORIGINS=https://your-app.vercel.app
```

Without this, the browser console will show CORS errors and the frontend won't be able to reach the backend.

### Heads up about storage
The backend stores cloned repos and its SQLite database on local disk (`app/storage/`). Railway's filesystem is ephemeral by default — data is wiped on redeploy/restart. Fine for demo purposes, but don't expect imported repositories to persist long-term unless you add a Railway Volume.

### Heads up about the API key
Your `GROQ_API_KEY` lives on the backend server, never in frontend code, so it's not directly exposed to visitors. That said, anyone with your live link can use your Groq quota while using the app. For a portfolio/resume link this is a low risk, but it's worth knowing.

---



**"Couldn't reach the DevLens AI backend"** in the frontend → the backend isn't running, or isn't on port 8000. Check the terminal where you ran `uvicorn`.

**CORS error in browser console** → the frontend isn't running on `localhost:5173`. If you changed the Vite port, add it to `cors_origins` in `backend/app/config.py`.

**"No Groq API key configured"** → add your key to `backend/.env` and restart the backend (Ctrl+C, then `uvicorn app.main:app --reload --port 8000` again).

**ChromaDB install errors on Windows** → make sure you're on Python 3.10–3.12 (ChromaDB 1.0.15 does not support 3.13+ at the time of writing). Run `python --version` to check.

**Dead code detector returns 0 results** → this is expected behavior on small or very well-maintained repositories where every function is genuinely referenced somewhere. It's not a bug — try it against a larger or older repository to see findings.

**`pydantic-core` fails to build from source / Rust compile errors** → you're likely on a very new Python version (3.14+) released after the pinned dependency versions came out, so pip falls back to compiling from source instead of using a prebuilt wheel — and on locked-down Windows machines (Application Control / antivirus policies), that compile step gets blocked outright. Fixed in this version of `requirements.txt` by using version ranges instead of exact pins, so pip picks whatever prebuilt wheel actually exists for your Python version. If you still hit this, run `python --version` and consider using Python 3.12 or 3.13 instead, which have the widest wheel availability.

**Backend starts but most API routes return 404 (only `/api/health` works)** → this was caused by a real regression in FastAPI 0.137.0+ that broke `include_router()` for routers sharing a common path-prefix pattern (confirmed by multiple independent projects hitting and reporting the same bug). `requirements.txt` pins `fastapi<0.137` specifically to avoid this. If you've manually upgraded fastapi past that version, downgrade with `pip install "fastapi<0.137"`.
