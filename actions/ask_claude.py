# actions/ask_claude.py
# The relay: routes a voice request to Claude (the architect) via the `claude` CLI,
# headless, scoped to the active project, with conversation memory across turns.
#
# Claude's job (defined by its own CLAUDE.md / system prompt later, Phase 3):
#   take the user's top-level decision -> brief Copilot to write code -> review -> report.
# This module is only the transport.

import json
import shutil
import subprocess
import uuid
from pathlib import Path

from actions.project_resolver import resolve

_SESSIONS_FILE = Path(__file__).resolve().parent.parent / "memory" / "claude_sessions.json"
_DEFAULT_TIMEOUT = 300  # seconds; raise once Copilot builds are wired in (Phase 3)


def _claude_bin() -> str:
    return shutil.which("claude") or r"C:\Users\Csaba\.local\bin\claude.exe"


def _load_sessions() -> dict:
    try:
        return json.loads(_SESSIONS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_session(key: str, session_id: str) -> None:
    sessions = _load_sessions()
    sessions[key] = session_id
    try:
        _SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SESSIONS_FILE.write_text(json.dumps(sessions, indent=2), encoding="utf-8")
    except Exception:
        pass


def _parse_result(stdout: str) -> tuple[str, str | None]:
    """Returns (text, session_id) from claude --output-format json."""
    try:
        data = json.loads(stdout)
        text = (data.get("result") or "").strip()
        sid = data.get("session_id")
        return text or stdout.strip(), sid
    except Exception:
        return stdout.strip(), None


def ask_claude(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    """
    parameters:
      request     : (required) what to ask Claude
      project     : optional project-name override; else auto-follow active VS Code
      new_session : optional bool; start a fresh conversation instead of resuming
    """
    p = parameters or {}
    request = (p.get("request") or "").strip()
    if not request:
        return "What would you like me to ask Claude, sir?"

    project_dir, source = resolve(p.get("project"))
    if project_dir is None:
        return ("I couldn't tell which project to use, sir. "
                "Open it in VS Code or name it explicitly.")

    if player:
        player.write_log(f"[ask_claude] {project_dir.name}: {request[:40]}")
    print(f"[ask_claude] project={project_dir} (via {source}) :: {request[:60]}")

    key = str(project_dir).lower()
    sid = _load_sessions().get(key)
    new_session = bool(p.get("new_session", False))

    cmd = [
        _claude_bin(), "-p", request,
        "--output-format", "json",
        "--permission-mode", "bypassPermissions",
        "--add-dir", str(project_dir),
    ]
    if sid and not new_session:
        cmd += ["--resume", sid]
    else:
        sid = str(uuid.uuid4())
        cmd += ["--session-id", sid]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(project_dir),
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=_DEFAULT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return f"Claude took too long on {project_dir.name} and timed out, sir."
    except Exception as e:
        return f"Could not reach Claude: {e}"

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        # a stale/parallel session can break --resume; retry once fresh
        if "--resume" in cmd and ("session" in err.lower() or not err):
            return ask_claude(
                {**p, "new_session": True},
                response, player, session_memory, speak,
            )
        return f"Claude errored on {project_dir.name}: {err[:200]}"

    text, returned_sid = _parse_result(proc.stdout)
    _save_session(key, returned_sid or sid)
    return text or "Claude returned nothing, sir."


if __name__ == "__main__":
    import sys
    req = " ".join(sys.argv[1:]) or "Reply with exactly: PONG"
    print(ask_claude({"request": req}))
