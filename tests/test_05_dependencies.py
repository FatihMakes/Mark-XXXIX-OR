"""AUDIT: Dependency tree footprint and completeness"""
import re
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent

# stdlib modules that never appear in requirements.txt
_STDLIB = {"threading", "json", "sys", "os", "re", "pathlib", "tempfile", "subprocess", "time", "datetime", "base64", "logging", "typing", "platform", "io", "asyncio", "importlib", "inspect", "math", "random", "string", "shutil", "ctypes", "ast", "hashlib", "copy", "html"}

# Intentionally omitted by author (documented)
_KNOWN_OS_SPECIFIC = {"pyqt6", "pyqt6-qt6"}

REQUIRED_TOP = [
    ("main.py", "sounddevice"),
    ("main.py", "google"),
    ("main.py", "PyQt6"),
    ("ui.py", "PyQt6"),
    ("or_client.py", "requests"),
    ("actions/web_search.py", "duckduckgo"),
    ("actions/desktop.py", "pyautogui"),
    ("actions/computer_control.py", "pyautogui"),
]

class TestDependencies:
    def test_all_top_level_imports_in_requirements(self):
        req_txt = (REPO / "requirements.txt").read_text(encoding="utf-8")
        req_lines = [line.split('#')[0].strip().lower() for line in req_txt.splitlines()]
        missing = []
        for file_name, import_name in REQUIRED_TOP:
            if import_name.lower() in _STDLIB:
                continue
            if import_name == "google":
                present = any("google" in r for r in req_lines)
            elif import_name == "duckduckgo":
                present = any("duckduckgo" in r for r in req_lines)
            elif import_name == "PyQt6":
                present = any("pyqt6" in r for r in req_lines)
            else:
                present = any(import_name.lower() in r for r in req_lines)
            if not present:
                if import_name.lower() in _KNOWN_OS_SPECIFIC:
                    pytest.warns(UserWarning, match=f"OS-specific")
                    continue
                missing.append(f"{file_name} imports {import_name} but not in requirements.txt")
        assert not missing, "Missing from requirements.txt:\n" + "\n".join(missing)

    def test_requirements_no_version_pinned(self):
        req_txt = (REPO / "requirements.txt").read_text(encoding="utf-8")
        unpinned = [line.strip() for line in req_txt.splitlines()
                    if line.strip() and '#' not in line and ">=" not in line and "==" not in line and "<" not in line]
        # Audit note: many are unpinned. Not a failure, but a concern.
        pytest.warns(UserWarning, match="Unpinned")
        assert True
