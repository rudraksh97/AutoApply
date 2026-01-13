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

