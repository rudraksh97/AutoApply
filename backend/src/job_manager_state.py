import json
import os
from datetime import datetime

class JobManagerState:
    """Manages the running state of the background job manager."""

    META_FILE = "data/job_manager_meta_data.json"

    @classmethod
    def _read_state(cls):
        if not os.path.exists(cls.META_FILE):
             # Default state
             return {
                "is_running": False,
                "last_status_change": datetime.now().isoformat(),
                "can_start": False,
                "validation_errors": []
             }
        try:
            with open(cls.META_FILE, 'r') as f:
                return json.load(f)
        except Exception:
             # Fallback if corrupt
             return {
                "is_running": False,
                "last_status_change": datetime.now().isoformat(),
                "can_start": False,
                "validation_errors": ["Corrupt metadata file"]
             }

    @classmethod
    def _write_state(cls, state):
        with open(cls.META_FILE, 'w') as f:
            json.dump(state, f, indent=2)

    @classmethod
    def is_running(cls) -> bool:
        """Check if the job manager is currently allowed to run."""
        state = cls._read_state()
        return state.get("is_running", False)

    @classmethod
    def set_running(cls, is_running: bool):
        """Update the running state."""
        state = cls._read_state()
        state["is_running"] = is_running
        state["last_status_change"] = datetime.now().isoformat()
        cls._write_state(state)

    @classmethod
    def get_status(cls):
        """Get full status object."""
        return cls._read_state()
