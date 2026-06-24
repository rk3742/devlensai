"""
DevLens AI — Codebase Intelligence Platform
Main FastAPI application entrypoint.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.routers import repositories, chat, documentation, quality, advanced

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("devlens")

app = FastAPI(
    title="DevLens AI",
    description="AI-powered codebase intelligence platform — understand any repository in plain English.",
    version="1.0.0",
)

# CORS is configured explicitly (not "*") so the frontend's exact origin must
# match — this is what the project spec means by "no CORS errors": getting
# this list right up front rather than discovering mismatches at runtime.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info(f"DevLens AI backend started. AI provider: {settings.ai_provider}")
    if settings.ai_provider == "groq" and not settings.groq_api_key:
        logger.warning(
            "AI_PROVIDER is 'groq' but GROQ_API_KEY is not set. AI features will fail until "
            "you add a free key from https://console.groq.com/keys to your .env file."
        )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception on {request.method} {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected server error occurred. Check the backend logs for details."},
    )


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "ai_provider": settings.ai_provider,
        "groq_configured": bool(settings.groq_api_key),
    }


app.include_router(repositories.router)
app.include_router(chat.router)
app.include_router(documentation.router)
app.include_router(quality.router)
app.include_router(advanced.router)
