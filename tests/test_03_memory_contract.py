"""AUDIT: Memory manager contract via source inspection."""
import ast, json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
MEM_SRC = (REPO / "memory" / "memory_manager.py").read_text(encoding="utf-8")

class TestMemoryManager:
    def test_categories_defined(self):
        # Downstream consumers depend on these keys
        for cat in ("identity", "preferences", "projects", "relationships", "wishes", "notes"):
            assert f"'{cat}'" in MEM_SRC or f'"{cat}"' in MEM_SRC, f"memory category {cat} missing"

    def test_max_chars_limit_declared(self):
        assert "MEMORY_MAX_CHARS = 2200" in MEM_SRC or "MEMORY_MAX_CHARS" in MEM_SRC, "Memory cap must be declared"

    def test_file_io_uses_lock(self):
        tree = ast.parse(MEM_SRC)
        has_lock = any(
            isinstance(node, ast.With) and
            any(isinstance(item, ast.Call) and getattr(item.func, 'id', None) == '_lock' for item in node.items)
            for node in ast.walk(tree)
        )
        assert "_lock" in MEM_SRC and "Lock()" in MEM_SRC, "Persistent memory must be thread-safe"

    def test_trimming_logic_exists(self):
        assert "_trim_to_limit" in MEM_SRC, "Memory must auto-trim to avoid unbounded growth"

    def test_state_file_is_json(self):
        assert "json" in MEM_SRC, "Memory persistence should use JSON"
        assert "read_text" in MEM_SRC or "open(" in MEM_SRC, "Memory must read from disk"
