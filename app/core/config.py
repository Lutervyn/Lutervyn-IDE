import os
import json
from pathlib import Path

class ConfigManager:
    """Manages IDE configuration and state persistence."""
    
    _INSTANCE = None

    @classmethod
    def get_instance(cls):
        if cls._INSTANCE is None:
            cls._INSTANCE = cls()
        return cls._INSTANCE

    def __init__(self):
        # Use a hidden directory in the user's home folder
        self.config_dir = Path(os.path.expanduser("~/.lutervyn_ide"))
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "state.json"
        
        # Load existing settings or start fresh
        self.settings = self._load()

    def _load(self):
        """Load state from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[Config] Error loading state: {e}")
        return {}

    def save(self):
        """Save current state to JSON file."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving state: {e}")

    def get(self, key, default=None):
        """Retrieve a value from the state."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Update a value and save immediately."""
        self.settings[key] = value
        self.save()

# Global singleton access
config = ConfigManager.get_instance()
