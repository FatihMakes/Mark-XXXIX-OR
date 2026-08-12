from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent

def load_settings():
    cfg_path = BASE_DIR / "config" / "settings.json"
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def load_api_keys():
    key_path = BASE_DIR / "config" / "api_keys.json"
    try:
        return json.loads(key_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
