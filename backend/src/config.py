"""
Configuration management for the AutoApply application.

This module provides handles for persistent configuration settings, such as 
RSS feed URLs and API keys, stored in local JSON and .env files.
"""

import os
import json
import uuid
from dotenv import set_key, load_dotenv

# Load env vars
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
LLMS_FILE = os.path.join(DATA_DIR, "llms.json")
WORKFLOWS_FILE = os.path.join(DATA_DIR, "workflows.json")
WORKFLOW_LLM_FILE = os.path.join(DATA_DIR, "workflow_llm.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

class ConfigManager:
    """
    Manages application configuration, including LLM inventory, workflows, and keys.
    """
    def __init__(self):
        self._ensure_config()

    def _ensure_config(self):
        """Creates data directory and config files if they do not exist."""
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
        
        # Ensure config.json exists
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"rss_feeds": [], "user_llm_configs": []}, f)
        
        # Ensure we have user_llm_configs structure
        data = self._load_json(CONFIG_FILE)
        if "user_llm_configs" not in data:
            data["user_llm_configs"] = []
            self._save_json(CONFIG_FILE, data)

    def _load_json(self, path):
        if not os.path.exists(path):
            return [] if path.endswith("s.json") else {} # List for definitions, Dict for config
        with open(path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return [] if path.endswith("s.json") else {}

    def _save_json(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    # =========================================================================
    # RSS Feeds (Legacy but kept)
    # =========================================================================

    def get_feeds(self):
        data = self._load_json(CONFIG_FILE)
        feeds = data.get("rss_feeds", [])
        # Normalization
        normalized = []
        for feed in feeds:
            if isinstance(feed, str):
                normalized.append({"url": feed, "name": ""})
            else:
                normalized.append(feed)
        return normalized

    def add_feed(self, url, name):
        feeds = self.get_feeds()
        for feed in feeds:
            if feed["url"] == url: return False
            if feed["name"] == name: return False
        feeds.append({"url": url, "name": name})
        
        data = self._load_json(CONFIG_FILE)
        data["rss_feeds"] = feeds
        self._save_json(CONFIG_FILE, data)
        return True

    def remove_feed(self, url):
        feeds = self.get_feeds()
        for i, feed in enumerate(feeds):
            if feed["url"] == url:
                feeds.pop(i)
                data = self._load_json(CONFIG_FILE)
                data["rss_feeds"] = feeds
                self._save_json(CONFIG_FILE, data)
                return True
        return False

    # =========================================================================
    # LLM SDK Definitions (llms.json)
    # =========================================================================

    def get_sdk_definitions(self):
        """Returns the list of supported LLM SDKs."""
        return self._load_json(LLMS_FILE)

    def get_sdk_definition(self, sdk_id):
        sdks = self.get_sdk_definitions()
        for sdk in sdks:
            if sdk["id"] == sdk_id:
                return sdk
        return None

    # =========================================================================
    # User LLM Configuration (config.json -> user_llm_configs)
    # =========================================================================

    def get_user_configs(self):
        """Returns the user's configured LLM keys."""
        data = self._load_json(CONFIG_FILE)
        return data.get("user_llm_configs", [])

    def add_user_config(self, sdk_id, name, api_key, plan_type, daily_limit=None):
        """
        Adds a new LLM configuration.
        """
        data = self._load_json(CONFIG_FILE)
        configs = data.get("user_llm_configs", [])

        # Get default limit from SDK if not provided
        sdk = self.get_sdk_definition(sdk_id)
        if daily_limit is None and sdk:
            daily_limit = sdk.get("daily_token_limit", 1000000)

        new_config = {
            "id": str(uuid.uuid4()),
            "sdk_id": sdk_id,
            "name": name,
            "api_key": api_key,
            "plan_type": plan_type,
            "daily_token_limit": daily_limit,
            "tokens_used_today": 0,
            "last_used_at": None,
            "reset_at": None # Will be set by TokenManager
        }
        
        configs.append(new_config)
        data["user_llm_configs"] = configs
        self._save_json(CONFIG_FILE, data)
        return new_config

    def update_user_config(self, config_id, updates: dict):
        """Updates an existing config."""
        data = self._load_json(CONFIG_FILE)
        configs = data.get("user_llm_configs", [])
        
        found = False
        for cfg in configs:
            if cfg["id"] == config_id:
                cfg.update(updates)
                found = True
                break
        
        if found:
            self._save_json(CONFIG_FILE, data)
            return True
        return False

    def remove_user_config(self, config_id):
        data = self._load_json(CONFIG_FILE)
        configs = data.get("user_llm_configs", [])
        
        initial_len = len(configs)
        configs = [c for c in configs if c["id"] != config_id]
        
        if len(configs) < initial_len:
            data["user_llm_configs"] = configs
            self._save_json(CONFIG_FILE, data)
            return True
        return False

    # =========================================================================
    # Workflows (workflows.json & workflow_llm.json)
    # =========================================================================

    def get_workflows(self):
        """Returns available workflow steps."""
        return self._load_json(WORKFLOWS_FILE)

    def get_workflow_links(self):
        """Returns mappings between workflows and user configs."""
        return self._load_json(WORKFLOW_LLM_FILE)

    def link_llm_to_workflow(self, workflow_id, llm_config_id):
        """Links a user LLM config to a workflow step."""
        links = self.get_workflow_links()
        
        # Check if already linked
        for link in links:
            if link["workflow_id"] == workflow_id and link["llm_config_id"] == llm_config_id:
                return True
                
        links.append({"workflow_id": workflow_id, "llm_config_id": llm_config_id})
        self._save_json(WORKFLOW_LLM_FILE, links)
        return True

    def unlink_llm_from_workflow(self, workflow_id, llm_config_id):
        links = self.get_workflow_links()
        new_links = [l for l in links if not (l["workflow_id"] == workflow_id and l["llm_config_id"] == llm_config_id)]
        
        if len(new_links) < len(links):
            self._save_json(WORKFLOW_LLM_FILE, new_links)
            return True
        return False
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def get_api_key(self, key_name):
        """Legacy helper for code that still checks env vars directly."""
        return os.getenv(key_name)

    def get_ats_prompts(self):
        data = self._load_json(CONFIG_FILE)
        return data.get("ats_prompts", {})

    def set_ats_prompts(self, prompts):
        data = self._load_json(CONFIG_FILE)
        data["ats_prompts"] = prompts
        self._save_json(CONFIG_FILE, data)
