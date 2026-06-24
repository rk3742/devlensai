"""
Orchestrates the full analysis pipeline for a repository: ingest files,
build the structure summary, index for RAG, and run static quality checks.
Runs as a background task so the API can return immediately and the
frontend can poll status.
"""
import json
import logging
import traceback

from app import db
from app.services.ingestion import (
    AnalyzableFile, walk_repository, read_file_safely, IngestionError,
)
from app.services.structure_analyzer import summarize_structure
from app.services.indexing import index_repository_files, delete_repository_index
from app.services.quality_analyzer import detect_dead_code, detect_technical_debt

logger = logging.getLogger("devlens.analysis")


def run_full_analysis(repo_id: str, repo_path) -> None:
    """
    Synchronous pipeline, intended to be invoked inside a FastAPI BackgroundTask
    or a thread. Updates the repository's status in the DB as it progresses so
    the frontend can poll for completion.
    """
    try:
        db.update_repository(repo_id, status="analyzing")

        files: list[AnalyzableFile] = walk_repository(repo_path)
        if not files:
            db.update_repository(
                repo_id, status="failed",
                error_message="No analyzable source files were found in this repository "
                               "(after filtering build artifacts, binaries, and dependency folders).",
            )
            return

        # Read content once, reuse across structure/indexing/quality passes.
        files_with_content: list[tuple[str, str, str]] = []
        for f in files:
            content = read_file_safely(f.abs_path)
            files_with_content.append((f.rel_path, f.language, content))

        # Persist file metadata.
        db.bulk_insert_files(repo_id, [
            {
                "rel_path": f.rel_path,
                "language": f.language,
                "size_bytes": f.size_bytes,
                "line_count": content.count("\n") + 1,
            }
            for f, (_, _, content) in zip(files, files_with_content)
        ])

        # Structure summary.
        structure = summarize_structure(files)
        db.update_repository(
            repo_id,
            file_count=len(files),
            languages=json.dumps(structure["languages"]),
            structure_json=json.dumps(structure),
        )

        # Vector index for RAG (Module 4 / Ask Questions).
        chunk_count = index_repository_files(repo_id, files_with_content)
        db.update_repository(repo_id, total_chunks=chunk_count)

        # Static quality analysis (Module 6 / 7).
        dead_code_findings = detect_dead_code(files_with_content)
        tech_debt_findings = detect_technical_debt(files_with_content)
        db.clear_findings(repo_id)
        if dead_code_findings:
            db.bulk_insert_findings(repo_id, dead_code_findings)
        if tech_debt_findings:
            db.bulk_insert_findings(repo_id, tech_debt_findings)

        db.update_repository(repo_id, status="ready")
        logger.info(f"Analysis complete for repo {repo_id}: {len(files)} files, {chunk_count} chunks")

    except IngestionError as e:
        db.update_repository(repo_id, status="failed", error_message=str(e))
    except Exception as e:
        logger.error(f"Unexpected analysis failure for repo {repo_id}: {traceback.format_exc()}")
        db.update_repository(
            repo_id, status="failed",
            error_message=f"Unexpected error during analysis: {str(e)[:300]}",
        )


def cleanup_repository(repo_id: str, repo_path) -> None:
    delete_repository_index(repo_id)
    import shutil
    shutil.rmtree(repo_path, ignore_errors=True)
