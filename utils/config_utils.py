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

# MQTT configuration utilities
def load_mqtt_config():
    """Loads MQTT configuration from config.json (project root). Returns dict or empty dict."""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("mqtt_cfg", {})
        except Exception:
            return {}
    return {}

def save_mqtt_config(cfg):
    """Saves MQTT configuration into config.json under key 'mqtt_cfg'. Returns success boolean."""
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))
    try:
        existing = {}
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing["mqtt_cfg"] = cfg
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4)
        return True
    except Exception:
        return False

