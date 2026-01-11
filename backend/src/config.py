import os
import json
from dotenv import set_key

CONFIG_FILE = "data/config.json"
ENV_FILE = ".env"

class ConfigManager:
    def __init__(self):
        self._ensure_config()

    def _ensure_config(self):
        if not os.path.exists("data"):
            os.makedirs("data")
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'w') as f:
                json.dump({"rss_feeds": []}, f)

    def get_feeds(self):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
        return data.get("rss_feeds", [])

    def add_feed(self, url):
        feeds = self.get_feeds()
        if url not in feeds:
            feeds.append(url)
            self._save_feeds(feeds)
            return True
        return False

    def remove_feed(self, url):
        feeds = self.get_feeds()
        if url in feeds:
            feeds.remove(url)
            self._save_feeds(feeds)
            return True
        return False

    def _save_feeds(self, feeds):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"rss_feeds": feeds}, f, indent=2)

    def set_api_key(self, key_name, key_value):
        # Create .env if not exists
        if not os.path.exists(ENV_FILE):
             with open(ENV_FILE, 'w') as f:
                 pass
        set_key(ENV_FILE, key_name, key_value)

    def get_api_key(self, key_name):
        return os.getenv(key_name)
