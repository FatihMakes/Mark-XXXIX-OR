from pathlib import Path
from datetime import datetime

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "actions.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_action(action: str, details: str = ""):
    try:
        ts = datetime.utcnow().isoformat()
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{ts} | {action} | {details}\n")
    except Exception:
        pass
