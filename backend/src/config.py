"""
Configuration management for the AutoApply application.

This module provides handles for persistent configuration settings, such as 
RSS feed URLs and API keys, stored in local JSON and .env files.
"""

import os
import json
from dotenv import set_key

CONFIG_FILE = "data/config.json"
ENV_FILE = ".env"

class ConfigManager:
    """
    Manages application configuration and API keys.

    Handles discovery, addition, and removal of RSS feeds, as well as
    securely persisting environment variables like API keys.
    """
    def __init__(self):
        """Initializes the manager and ensures the config data file exists."""
        self._ensure_config()

    def _ensure_config(self):
        """Creates the data directory and config JSON file if they do not exist."""
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"rss_feeds": []}, f)

    def get_feeds(self):
        """
        Retrieves the list of configured RSS feeds.

        Returns:
            list: A list of feed objects with 'url' and 'name' fields.
                  For backwards compatibility, string entries are converted to objects.
        """
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
        feeds = data.get("rss_feeds", [])
        # Handle backwards compatibility: convert old string entries to objects
        normalized = []
        for feed in feeds:
            if isinstance(feed, str):
                # Old format - user will need to re-add with a name
                normalized.append({"url": feed, "name": ""})
            else:
                normalized.append(feed)
        return normalized

    def add_feed(self, url, name):
        """
        Adds a new RSS feed to the configuration.

        Args:
            url (str): The URL of the RSS feed to add.
            name (str): The distinct name for this feed.

        Returns:
            bool: True if the feed was added, False if URL or name already exists.
        """
        feeds = self.get_feeds()
        # Check for duplicate URL or name
        for feed in feeds:
            if feed["url"] == url:
                return False  # URL already exists
            if feed["name"] == name:
                return False  # Name already exists
        feeds.append({"url": url, "name": name})
        self._save_feeds(feeds)
        return True

    def remove_feed(self, url):
        """
        Removes an RSS feed from the configuration by URL.

        Args:
            url (str): The URL of the RSS feed to remove.

        Returns:
            bool: True if the feed was removed, False if it was not found.
        """
        feeds = self.get_feeds()
        for i, feed in enumerate(feeds):
            if feed["url"] == url:
                feeds.pop(i)
                self._save_feeds(feeds)
                return True
        return False

    def _save_feeds(self, feeds):
        """Saves the feed list to the config JSON file."""
        data = self._load_config()
        data["rss_feeds"] = feeds
        self._save_config(data)

    def _load_config(self):
        """Loads the full config from the JSON file."""
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)

    def _save_config(self, data):
        """Saves the full config to the JSON file."""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(data, f, indent=2)

    def get_selected_model(self):
        """
        Retrieves the currently selected LLM model.

        Returns:
            str: The model identifier, or default if not set.
        """
        data = self._load_config()
        return data.get("selected_model", "anthropic/claude-sonnet-4")

    def set_selected_model(self, model_id):
        """
        Sets the selected LLM model.

        Args:
            model_id (str): The OpenRouter model identifier.
        """
        data = self._load_config()
        data["selected_model"] = model_id
        self._save_config(data)

    def get_plan_type(self):
        """
        Retrieves the current plan type ('paid' or 'free').
        Defaults to 'paid'.
        """
        data = self._load_config()
        return data.get("plan_type", "paid")

    def set_plan_type(self, plan_type):
        """
        Sets the current plan type.
        """
        data = self._load_config()
        data["plan_type"] = plan_type
        self._save_config(data)

    def get_free_configs(self):
        """
        Retrieves the list of model configurations for the free plan.
        """
        data = self._load_config()
        return data.get("free_configs", [])

    def set_free_configs(self, configs):
        """
        Saves the list of free model configurations.
        """
        data = self._load_config()
        data["free_configs"] = configs
        self._save_config(data)

    def add_free_config(self, sdk, model, api_key):
        """
        Adds a new model configuration to the free plan.
        """
        configs = self.get_free_configs()
        configs.append({
            "sdk": sdk,
            "model": model,
            "api_key": api_key,
            "usage_count": 0
        })
        self.set_free_configs(configs)

    def remove_free_config(self, index):
        """
        Removes a model configuration from the free plan by index.
        """
        configs = self.get_free_configs()
        if 0 <= index < len(configs):
            configs.pop(index)
            self.set_free_configs(configs)
            return True
        return False

    def set_api_key(self, key_name, key_value):
        """
        Updates an API key in the local .env file.

        Args:
            key_name (str): The name of the environment variable.
            key_value (str): The secret value to store.
        """
        # Create .env if not exists
        if not os.path.exists(ENV_FILE):
             with open(ENV_FILE, 'w') as f:
                 pass
        set_key(ENV_FILE, key_name, key_value)

    def get_api_key(self, key_name):
        """
        Retrieves an API key from environmental variables.

        Args:
            key_name (str): The name of the key to fetch.

        Returns:
            str: The value of the key, or None if not found.
        """
        return os.getenv(key_name)

    def get_ats_prompts(self):
        """
        Retrieves the custom ATS prompts from configuration.
        """
        data = self._load_config()
        defaults = {
            "calculate_score": (
                "You are an ATS (Applicant Tracking System) expert. "
                "Evaluate the provided Resume against the Job Description.\n\n"
                "--- JOB DESCRIPTION ---\n{{job_description}}\n\n"
                "--- RESUME TEXT ---\n{{resume_text}}\n\n"
                "Analyze the match and provide:\n"
                "1. A list of missing keywords (crucial skills found in JD but not in Resume).\n"
                "2. A list of matched keywords (skills found in both).\n"
                "3. A score from 0 to 100 based on keyword density and relevance.\n"
                "4. A detailed justification object with keys: keyword_match, skill_depth, role_fit, experience_relevance, education_fit, parsing_quality."
            ),
            "tailor_resume": (
                "You are an ATS-optimization engine used by Big Tech recruiting platforms.\n"
                "Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job description, while preserving structure, honesty, and formatting.\n\n"
                "You will be given:\n"
                "- initial_ats_score: {{initial_ats_score}}\n"
                "- missing_keywords: {{missing_keywords}}\n"
                "- matched_keywords: {{matched_keywords}}\n"
                "- justification: {{justification}}\n"
                "- job_description: {{job_description}}\n"
                "- old_resume_code (LaTeX): {{resume_text}}\n\n"
                "You must modify ONLY the LaTeX content, not the section structure.\n\n"
                "--------------------------------\n"
                "STRICT RULES\n\n"
                "1) DO NOT:\n"
                "- Add new sections\n"
                "- Remove any existing section\n"
                "- Rename section headers\n"
                "- Change the structure of the Skills section subheadings\n"
                "- Delete any existing skills\n\n"
                "2) YOU MUST:\n"
                "- Add all missing_keywords into appropriate places:\n"
                "  - Skills section (correct subheading)\n"
                "  - Experience bullet points\n"
                "  - Project descriptions\n"
                "- If a missing skill is critical (core job requirement), then you MUST:\n"
                "  - Replace or enhance technologies used in experience/projects to include that skill\n"
                "  - Add appropriate frameworks if language matches (e.g. Java -> Spring Boot)\n\n"
                "3) The resume must remain:\n"
                "- Technically believable\n"
                "- Internally consistent\n"
                "- ATS-readable\n"
                "- Optimized for keyword density and semantic matching\n\n"
                "--------------------------------\n"
                "OPTIMIZATION TARGET\n"
                "You must simulate ATS scoring internally and ensure final_score >= 90.\n"
                "If the rewritten resume would not reach 90, you must further optimize until it does.\n"
            )
        }
        return data.get("ats_prompts", defaults)

    def set_ats_prompts(self, prompts):
        """
        Updates the custom ATS prompts in configuration.
        """
        data = self._load_config()
        data["ats_prompts"] = prompts
        self._save_config(data)

