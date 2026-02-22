"""
SystemState helper: DB-backed replacement for job_manager_meta_data.json and poller_status.json.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Keys stored in SystemState table
JOB_MANAGER_KEY = "job_manager_state"
POLLER_STATUS_KEY = "poller_status"


def _get_db():
    from src.db import SessionLocal
    return SessionLocal()


def _get_state(key: str, default: dict) -> dict:
    db = _get_db()
    try:
        from src.models import SystemState
        row = db.query(SystemState).filter(SystemState.key == key).first()
        if row and row.value:
            return row.value
        return default
    except Exception as e:
        logger.error(f"Error reading SystemState key={key}: {e}")
        return default
    finally:
        db.close()


def _set_state(key: str, value: dict):
    db = _get_db()
    try:
        from src.models import SystemState
        row = db.query(SystemState).filter(SystemState.key == key).first()
        if row:
            row.value = value
            row.updated_at = datetime.utcnow()
        else:
            row = SystemState(key=key, value=value)
            db.add(row)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error writing SystemState key={key}: {e}")
    finally:
        db.close()


class JobManagerState:
    """Manages the running state of the background job manager using DB."""

    _DEFAULT = {
        "is_running": False,
        "last_status_change": None,
        "can_start": False,
        "validation_errors": []
    }

    @classmethod
    def _read_state(cls) -> dict:
        return _get_state(JOB_MANAGER_KEY, cls._DEFAULT.copy())

    @classmethod
    def _write_state(cls, state: dict):
        _set_state(JOB_MANAGER_KEY, state)

    @classmethod
    def is_running(cls) -> bool:
        return cls._read_state().get("is_running", False)

    @classmethod
    def set_running(cls, is_running: bool):
        state = cls._read_state()
        state["is_running"] = is_running
        state["last_status_change"] = datetime.now().isoformat()
        cls._write_state(state)

    @classmethod
    def get_status(cls) -> dict:
        return cls._read_state()


class PollerState:
    """Manages the RSS poller status using DB (replaces poller_status.json)."""

    _DEFAULT = {
        "last_poll_time": 0,
        "total_polls": 0,
        "last_jobs_found": 0,
        "is_polling": False
    }

    @classmethod
    def get_status(cls) -> dict:
        return _get_state(POLLER_STATUS_KEY, cls._DEFAULT.copy())

    @classmethod
    def update(cls, **kwargs):
        state = cls.get_status()
        state.update(kwargs)
        _set_state(POLLER_STATUS_KEY, state)

    @classmethod
    def set_polling(cls, is_polling: bool):
        cls.update(is_polling=is_polling)

    @classmethod
    def record_poll(cls, jobs_found: int):
        import time
        cls.update(
            last_poll_time=int(time.time()),
            total_polls=cls.get_status().get("total_polls", 0) + 1,
            last_jobs_found=jobs_found,
            is_polling=False
        )
