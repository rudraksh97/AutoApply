import logging
import pytz
from datetime import datetime, timedelta
from src.config import ConfigManager

logger = logging.getLogger(__name__)

# Eastern Time Zone
EST = pytz.timezone('US/Eastern')

class TokenManager:
    """
    Manages token usage tracking and daily resets for LLM configurations.
    """
    def __init__(self):
        self.config_manager = ConfigManager()

    def record_usage(self, llm_config_id: str, tokens_used: int):
        """
        Updates the usage count for a specific LLM config.
        Also checks if a reset is needed before recording.
        """
        # 1. Check/Perform Reset First
        self._check_and_reset(llm_config_id)
        
        # 2. Record Usage
        configs = self.config_manager.get_user_configs()
        target_config = None
        for cfg in configs:
            if cfg["id"] == llm_config_id:
                target_config = cfg
                break
        
        if target_config:
            new_usage = target_config.get("tokens_used_today", 0) + tokens_used
            self.config_manager.update_user_config(llm_config_id, {
                "tokens_used_today": new_usage,
                "last_used_at": datetime.now(EST).isoformat()
            })
            logger.info(f"Recorded {tokens_used} tokens for {target_config['name']}. Total today: {new_usage}")

    def _check_and_reset(self, llm_config_id: str):
        """
        Checks if the daily reset time has passed and resets counters if needed.
        """
        configs = self.config_manager.get_user_configs()
        target_config = None
        for cfg in configs:
            if cfg["id"] == llm_config_id:
                target_config = cfg
                break
        
        if not target_config:
            return

        reset_at_str = target_config.get("reset_at")
        now = datetime.now(EST)

        # If no reset time set, set it to next 3:01 AM
        if not reset_at_str:
            next_reset = self._get_next_reset_time()
            self.config_manager.update_user_config(llm_config_id, {
                "reset_at": next_reset.isoformat(),
                "tokens_used_today": 0
            })
            return

        # Check if we passed the reset time
        reset_at = datetime.fromisoformat(reset_at_str)
        if now >= reset_at:
            logger.info(f"Daily reset triggered for {target_config['name']}")
            next_reset = self._get_next_reset_time()
            self.config_manager.update_user_config(llm_config_id, {
                "reset_at": next_reset.isoformat(),
                "tokens_used_today": 0
            })

    def _get_next_reset_time(self):
        """Returns the next occurrence of 3:01 AM EST."""
        now = datetime.now(EST)
        target = now.replace(hour=3, minute=1, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        return target
