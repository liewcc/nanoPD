import json
import os

UI_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "UI_config.json")

# Core Factory Defaults
DEFAULT_UI_CONFIG = {
    "title_size": "1.5rem",
    "label_size": "0.875rem",
    "info_size": "1.0rem",
    "code_font": "Consolas, Monaco, monospace",
    "code_size": "14px",
    "code_lh": "1.3",
    "logo_scale": 30
}

def load_ui_config():
    """Loads UI configuration from JSON, returning defaults if not found."""
    if os.path.exists(UI_CONFIG_PATH):
        try:
            with open(UI_CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                # Ensure all default keys exist
                full_cfg = DEFAULT_UI_CONFIG.copy()
                full_cfg.update(config)
                return full_cfg
        except Exception:
            return DEFAULT_UI_CONFIG.copy()
    return DEFAULT_UI_CONFIG.copy()

def save_ui_config(config):
    """Saves UI configuration to JSON."""
    try:
        with open(UI_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        return True
    except Exception:
        return False
