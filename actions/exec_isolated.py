"""
Exec isolated helper (autopilot stub)

This module provides a minimal execute_code_isolated(code) function that
intentionally does NOT execute untrusted code. It returns a timed_out=True
signal so the caller will fall back to a safer execution path or skip execution.

If you want to enable actual isolated execution, replace this stub with a
secure runner that executes user code inside a properly configured container/VM
with strict resource limits and sandboxing.
"""
import time

def execute_code_isolated(code: str, timeout: int = 10):
    """Stub runner: do not run code. Return a structure resembling a real runner.

    Returns:
      dict with keys: returncode, stdout, stderr, timed_out
    """
    # Log the request to a local file for audit (best-effort)
    try:
        with open('logs/exec_isolated_requests.log', 'a', encoding='utf-8') as f:
            f.write(f"{time.time()} | len={len(code)}\n")
    except Exception:
        pass

    # Signal that execution was not performed
    return {
        'returncode': None,
        'stdout': '',
        'stderr': 'exec_isolated stub: execution not performed',
        'timed_out': True,
    }
