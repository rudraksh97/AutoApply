"""
Database initialization module for AutoApply.

Design contract:
  - `init_db()` MUST be idempotent. Safe to call repeatedly.
  - All model classes must be imported here so that SQLAlchemy's metadata is
    populated before `create_all` is invoked.
  - This module is the SINGLE authoritative place that calls `create_all`.
    No other module should call it.
"""

import logging
from contextlib import contextmanager

from .db import engine, SessionLocal, Base  # noqa: F401

# ── Import every model so they register with Base.metadata ────────────────────
from .models import (  # noqa: F401
    User,
    Profile,
    Resume,
    Feed,
    Job,
    Settings,
    SystemState,
    WorkflowStep,
    WorkflowLLMLink,
    LLMConfig,
    UserProfile,
)

logger = logging.getLogger(__name__)

# ── Guard against repeated invocations in the same process ────────────────────
_DB_INITIALIZED = False


def init_db() -> None:
    """
    Idempotent database initializer.

    Uses SQLAlchemy's `create_all` which is a no-op for tables that already
    exist. The process-level guard (`_DB_INITIALIZED`) prevents redundant
    log noise and any future non-idempotent work added here.

    Safe to call from lifespan hooks. NOT safe to call from request handlers.
    """
    global _DB_INITIALIZED
    if _DB_INITIALIZED:
        logger.debug("init_db() skipped — already initialised in this process.")
        return

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("DB schema ensured (create_all completed).")
        _DB_INITIALIZED = True
    except Exception:
        logger.exception("FATAL: Database schema initialisation failed.")
        raise


@contextmanager
def get_connection():
    """
    Context manager for raw database connections.
    Required by DraftManager for raw SQL operations.
    """
    conn = engine.raw_connection()
    try:
        yield conn
    finally:
        conn.close()
