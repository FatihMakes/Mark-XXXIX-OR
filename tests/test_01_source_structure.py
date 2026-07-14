"""AUDIT: Repository structure and declared capabilities."""
import pytest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

class TestStructure:
    def test_main_entry_exists(self):
        assert (REPO / "main.py").exists(), "main.py is the advertised entry point"

    def test_requirements_txt_exists(self):
        assert (REPO / "requirements.txt").exists()

    def test_prompt_txt_exists(self):
        assert (REPO / "core" / "prompt.txt").exists(), "System prompt should be version controlled"

    def test_memory_module_exists(self):
        assert (REPO / "memory" / "memory_manager.py").exists()

    def test_all_actions_exist(self):
        expected = [
            "file_processor.py", "flight_finder.py", "open_app.py",
            "weather_report.py", "send_message.py", "reminder.py",
            "computer_settings.py", "screen_processor.py", "youtube_video.py",
            "desktop.py", "browser_control.py", "file_controller.py",
            "code_helper.py", "dev_agent.py", "web_search.py",
            "computer_control.py", "game_updater.py",
        ]
        for name in expected:
            assert (REPO / "actions" / name).exists(), f"{name} missing"
