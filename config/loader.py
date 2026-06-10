# config/loader.py
# Unified configuration loader with API key management

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def get_base_dir() -> Path:
    """Get base directory of the project."""
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def get_api_config_path() -> Path:
    """Get path to api_keys.json config file."""
    return get_base_dir() / "config" / "api_keys.json"


def _load_api_keys_json() -> dict:
    """Load API keys from JSON config file."""
    api_path = get_api_config_path()
    if not api_path.exists():
        return {}
    try:
        return json.loads(api_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def get_api_key(key_name: str) -> str | None:
    """
    Load API key from environment variable with fallback to JSON config.
    Priority: .env -> os.environ -> config/api_keys.json

    Supports keys:
    - GEMINI_API_KEY / gemini_api_key
    - SERPER_API_KEY / serper_api_key
    - OPENROUTER_API_KEY / openrouter_api_key
    """
    # First try environment variable (from .env or system)
    value = os.getenv(key_name)
    if value:
        return value

    # Fallback to JSON config
    api_keys = _load_api_keys_json()

    # Map environment variable names to JSON keys
    key_map = {
        "GEMINI_API_KEY": "gemini_api_key",
        "GEMINI_API_KEY.lower()": "gemini_api_key",
        "SERPER_API_KEY": "serper_api_key",
        "OPENROUTER_API_KEY": "openrouter_api_key",
    }

    json_key = key_map.get(key_name, key_name.lower())
    return api_keys.get(json_key)


def get_gemini_api_key() -> str | None:
    """Get Gemini API key."""
    return get_api_key("GEMINI_API_KEY")


def get_serper_api_key() -> str | None:
    """Get Serper API key."""
    return get_api_key("SERPER_API_KEY")


def get_openrouter_api_key() -> str | None:
    """Get OpenRouter API key."""
    return get_api_key("OPENROUTER_API_KEY")


def get_or_client():
    """Get OpenRouter client if API key is available."""
    api_key = get_openrouter_api_key()
    if not api_key:
        return None
    try:
        from or_client import Client
        return Client(api_key=api_key)
    except ImportError:
        return None
