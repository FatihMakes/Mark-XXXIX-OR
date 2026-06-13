# actions/project_resolver.py
# Resolves which project folder Jarvis should aim Claude+Copilot at.
#
# Resolution order:
#   1. Explicit name from the voice request  ("...the lead-flow project")
#   2. Auto-follow: the folder open in the active VS Code window
#   3. Sticky fallback: the last project we resolved (memory/current_project.json)
#
# Hard boundary: the resolved path MUST live directly under PROJECTS_ROOT.

import json
import subprocess
from pathlib import Path

PROJECTS_ROOT = Path(r"C:\Users\Csaba\Projects")
_STATE_FILE   = Path(__file__).resolve().parent.parent / "memory" / "current_project.json"
_VSCODE_SUFFIX = "Visual Studio Code"


# ── project listing / matching ────────────────────────────────────────────────

def list_projects() -> list[str]:
    """Folder names directly under the Projects root."""
    if not PROJECTS_ROOT.exists():
        return []
    return sorted(p.name for p in PROJECTS_ROOT.iterdir() if p.is_dir())


def _norm(s: str) -> str:
    return s.lower().replace("-", "").replace("_", "").replace(" ", "")


def _match_name(name: str) -> Path | None:
    """Map a spoken/typed project name to a real folder (fuzzy, separator-insensitive)."""
    if not name:
        return None
    target = _norm(name)
    projects = list_projects()
    # exact-ish first
    for p in projects:
        if _norm(p) == target:
            return PROJECTS_ROOT / p
    # then contains
    for p in projects:
        if target in _norm(p) or _norm(p) in target:
            return PROJECTS_ROOT / p
    return None


# ── auto-follow the active VS Code window ─────────────────────────────────────

def _vscode_titles() -> list[str]:
    try:
        import pygetwindow as gw
    except Exception:
        return []
    titles = []
    try:
        active = gw.getActiveWindow()
        if active and active.title and active.title.strip().endswith(_VSCODE_SUFFIX):
            titles.append(active.title)            # prefer the focused window
    except Exception:
        pass
    try:
        for t in gw.getAllTitles():
            if t and t.strip().endswith(_VSCODE_SUFFIX) and t not in titles:
                titles.append(t)
    except Exception:
        pass
    return titles


def _folder_from_title(title: str) -> str | None:
    """'file - folder - Visual Studio Code' -> 'folder'."""
    parts = [p.strip() for p in title.split(" - ")]
    if len(parts) < 2 or not parts[-1].endswith(_VSCODE_SUFFIX):
        return None
    folder = parts[-2]
    # strip dirty marker / admin prefix
    folder = folder.lstrip("●").strip()
    if folder.startswith("[Administrator]"):
        folder = folder.split("]", 1)[-1].strip()
    return folder or None


def active_vscode_folder() -> Path | None:
    for title in _vscode_titles():
        folder = _folder_from_title(title)
        if not folder:
            continue
        match = _match_name(folder)
        if match:
            return match
    return None


# ── sticky state ──────────────────────────────────────────────────────────────

def _load_sticky() -> Path | None:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        p = Path(data.get("current_project", ""))
        if p.exists():
            return p
    except Exception:
        pass
    return None


def _save_sticky(path: Path) -> None:
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(
            json.dumps({"current_project": str(path)}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


# ── public API ────────────────────────────────────────────────────────────────

def _within_boundary(path: Path) -> bool:
    try:
        return path.resolve().parent == PROJECTS_ROOT.resolve() and path.exists()
    except Exception:
        return False


def resolve(name: str | None = None) -> tuple[Path | None, str]:
    """
    Returns (project_path, source). source is one of:
      'name' | 'vscode' | 'sticky' | 'none'
    Only returns a path that sits directly under PROJECTS_ROOT.
    """
    if name:
        m = _match_name(name)
        if m and _within_boundary(m):
            _save_sticky(m)
            return m, "name"

    auto = active_vscode_folder()
    if auto and _within_boundary(auto):
        _save_sticky(auto)
        return auto, "vscode"

    sticky = _load_sticky()
    if sticky and _within_boundary(sticky):
        return sticky, "sticky"

    return None, "none"


def open_in_vscode(path: Path, replace: bool = False) -> str:
    """Open a folder in VS Code. replace=True swaps the current window."""
    if not _within_boundary(path):
        return f"Refused: '{path}' is outside the projects boundary."
    args = ["code"] + (["-r"] if replace else []) + [str(path)]
    try:
        subprocess.Popen(args, shell=True)
        return f"Opened {path.name} in VS Code."
    except Exception as e:
        return f"Could not open VS Code: {e}"


if __name__ == "__main__":
    # quick self-test
    print("Projects root:", PROJECTS_ROOT)
    print("Projects:", list_projects())
    print("VS Code titles:", _vscode_titles())
    print("Active VS Code folder:", active_vscode_folder())
    path, source = resolve()
    print(f"resolve() -> {path}  (via {source})")
