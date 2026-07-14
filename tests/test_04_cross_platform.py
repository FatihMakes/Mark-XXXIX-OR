"""AUDIT: Cross-platform abstraction coverage"""
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

def load_module_text(name):
    return (REPO / "actions" / name).read_text(encoding="utf-8")

class TestCrossPlatform:
    def test_computer_settings_has_three_branches(self):
        src = load_module_text("computer_settings.py")
        assert 'if _OS == "Windows"' in src
        assert 'if _OS == "Darwin"' in src
        assert 'elif _OS == "Linux"' in src or 'if _OS == "Linux"' in src

    def test_desktop_has_os_agnostic_fallbacks(self):
        src = load_module_text("desktop.py")
        assert "_OS ==" in src or "_get_os" in src
        assert "pyautogui" in src or "_PYAUTOGUI" in src

    def test_ui_detects_platform(self):
        src = (REPO / "ui.py").read_text(encoding="utf-8")
        assert 'platform.system()' in src

    def test_computer_control_not_only_windows(self):
        src = load_module_text("computer_control.py")
        assert "Windows" in src
        assert "Darwin" in src or "Linux" in src
