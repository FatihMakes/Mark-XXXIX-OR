"""
Dynamic skill loader — lets J.A.R.V.I.S. extend himself at runtime.

Any `skills/<name>.py` that exposes:
    MANIFEST = {"name": str, "description": str, "parameters": {...gemini schema...}}
    def run(parameters, player=None, speak=None) -> str
is auto-discovered and registered as a Gemini tool — no edits to main.py needed.

This is the mechanism behind the `self_upgrade` action: Jarvis writes a new file
here, and on the next session it becomes a callable tool.
"""
import importlib.util
import traceback
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent
_RESERVED = {"__init__.py", "loader.py"}


def load_skills():
    """Discover skills. Returns (declarations: list[dict], dispatch: dict[name -> callable])."""
    declarations = []
    dispatch = {}
    for f in sorted(SKILLS_DIR.glob("*.py")):
        if f.name in _RESERVED:
            continue
        try:
            spec = importlib.util.spec_from_file_location(f"skills.{f.stem}", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            manifest = getattr(mod, "MANIFEST", None)
            run = getattr(mod, "run", None)
            if not (isinstance(manifest, dict) and callable(run)):
                continue
            name = manifest.get("name")
            if not name or name in dispatch:
                continue
            # Normalize: ensure a parameters block exists.
            manifest.setdefault("parameters", {"type": "OBJECT", "properties": {}})
            declarations.append({
                "name": name,
                "description": manifest.get("description", name),
                "parameters": manifest["parameters"],
            })
            dispatch[name] = run
        except Exception:
            print(f"[Skills] Failed to load {f.name}:")
            traceback.print_exc()
    return declarations, dispatch


def list_skill_files():
    return [f.name for f in sorted(SKILLS_DIR.glob("*.py")) if f.name not in _RESERVED]
