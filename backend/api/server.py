"""
FastAPI server for the AutoApply application.

This module provides:
- REST API endpoints for job management, feeds, profiles, and drafts
- Background task for automated RSS polling and job processing
- Static file serving for resumes and generated documents
"""

import asyncio
import logging
import os
import uvicorn
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routers import admin, auth, drafts, feeds, jobs, profile, settings, test_feed
from api.repositories.sql_repo import SqlProfileRepository
from api.services.domain_services import ProfileService
from api.dependencies import get_current_user
from src.agent import BrowserAgent
from src.db import SessionLocal
from src.job_manager import JobManager
from src.resume_builder import ResumeBuilder
from src.services import DraftPreparationService
from src.models import User

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True,
    handlers=[
        logging.StreamHandler()
    ]
)

# =============================================================================
# Constants
# =============================================================================

DATA_DIRECTORIES = [
    "data",                          # Base data directory always exists
    "data/resumes/templates",        # Global LaTeX template storage
    "data/generated_resumes",        # Fallback for jobs without user context
    # Note: per-user dirs (data/{email}/resumes, /tex_resumes, /generated_resumes)
    # are created on-demand by the profile router and resume_builder.
]



# =============================================================================
# Application Setup
# =============================================================================

def _ensure_directories():
    """Create required data directories."""
    for directory in DATA_DIRECTORIES:
        os.makedirs(directory, exist_ok=True)


def _seed_workflow_steps() -> None:
    """
    Idempotent seed: insert WorkflowStep rows from workflows.json.
    Only inserts rows whose id is not already present in the DB.
    Never deletes or overwrites existing rows to preserve referential integrity
    with WorkflowLLMLink records.
    """
    import json
    from src.db import SessionLocal as _SL
    from src.models import WorkflowStep

    workflows_path = os.path.join("data", "workflows.json")
    if not os.path.exists(workflows_path):
        logging.warning(f"workflows.json not found at {workflows_path}; skipping seed.")
        return

    try:
        with open(workflows_path, "r") as f:
            steps = json.load(f)
    except Exception:
        logging.exception("Failed to parse workflows.json; skipping seed.")
        return

    db = _SL()
    try:
        inserted = 0
        for step in steps:
            step_id = step.get("id")
            if not step_id:
                logging.warning(f"Workflow step missing 'id' field; skipping: {step}")
                continue
            if not db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first():
                db.add(WorkflowStep(
                    id=step_id,
                    name=step.get("name", step_id),
                    description=step.get("description"),
                    required_capabilities=step.get("required_capabilities", []),
                ))
                inserted += 1
        if inserted:
            db.commit()
            logging.info(f"Seeded {inserted} WorkflowStep(s) into DB.")
        else:
            logging.debug("WorkflowStep catalogue already up-to-date; no rows inserted.")
    except Exception:
        db.rollback()
        logging.exception("Failed to seed WorkflowSteps.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.

    Startup sequence (each step is idempotent and failure-isolated):
      1. Ensure data directories exist.
      2. Initialize DB schema (single call, guarded against re-entry).
      3. Seed static workflow step catalogue (no-op if already seeded).
      4. Create default test user if absent.
      5. Safety-reset job manager state.
      6. Start background automation loop.
    """
    _ensure_directories()

    # ── Step 1: Schema init (single source of truth) ─────────────────────────
    from src.database import init_db
    init_db()

    # ── Step 2: Seed WorkflowStep catalogue ──────────────────────────────────
    _seed_workflow_steps()

    # ── Step 2.5: One-time migration of legacy config.json LLM entries ─────────
    try:
        from src.config import ConfigManager
        ConfigManager().migrate_legacy_llm_configs(user_id=None)
    except Exception:
        logging.exception("Legacy LLM config migration failed (non-fatal).")

    # ── Step 3: Ensure test user exists ──────────────────────────────────────
    from src.auth import get_password_hash
    from src.models import User
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "testuser").first():
            logging.info("Creating default test user 'testuser'.")
            db.add(User(
                username="testuser",
                email="test@example.com",
                hashed_password=get_password_hash("password123"),
                roles=["admin", "customer", "basic"]
            ))
            db.commit()
    except Exception:
        logging.exception("Failed to create test user.")
        db.rollback()
    finally:
        db.close()

    # ── Step 4: Safety-reset job manager ─────────────────────────────────────
    try:
        from src.job_manager_state import JobManagerState
        if JobManagerState.is_running():
            logging.warning("Forcing Job Manager to STOPPED on startup safety check.")
            JobManagerState.set_running(False)
    except Exception:
        logging.exception("Could not check/reset job manager state.")

    # ── Step 5: Background tasks handled externally ────────────────────────
    yield
    logging.info("API Server shutting down.")


app = FastAPI(
    title="AutoApply API",
    version="2.0.0",
    description="Draft-first job application preparation.",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers — Next.js proxy already maps /api to root
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(feeds.router)
app.include_router(jobs.router)
app.include_router(profile.router)
app.include_router(drafts.router)
app.include_router(settings.router)
app.include_router(test_feed.router)

# Static Files moved to after router inclusion for clarity
_ensure_directories()
app.mount("/data", StaticFiles(directory="data"), name="data")
app.mount("/resumes", StaticFiles(directory="data/resumes"), name="resumes")
app.mount("/generated_resumes", StaticFiles(directory="data/generated_resumes"), name="generated_resumes")
app.mount("/tex_resumes", StaticFiles(directory="data/tex_resumes"), name="tex_resumes")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info", access_log=True)
