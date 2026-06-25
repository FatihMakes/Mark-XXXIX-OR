import os
import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path

# Set up paths so we can import from database and memory modules
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.mongo_db import MongoDBHandler
from memory.memory_manager import update_memory, load_memory

def run_self_training(limit: int = 150) -> str:
    print("[Self-Training] Initializing database connection...")
    db = MongoDBHandler()
    if db.db is None:
        return "Failed to run self-training: MongoDB connection unavailable."

    print(f"[Self-Training] Fetching last {limit} chat entries from MongoDB...")
    chats = db.find("chat_history", limit=limit)
    if not chats:
        return "No chat history found in database to train with."

    # Sort by timestamp/ID if needed, but mongo find usually returns in order
    # Format the chat history into a string for Gemini analysis
    chat_lines = []
    for entry in chats:
        user = entry.get("user", "").strip()
        jarvis = entry.get("jarvis", "").strip()
        timestamp = entry.get("timestamp", "")
        if user or jarvis:
            chat_lines.append(f"[{timestamp}] User: {user}")
            chat_lines.append(f"[{timestamp}] Jarvis: {jarvis}")

    chat_corpus = "\n".join(chat_lines)
    print(f"[Self-Training] Loaded {len(chats)} conversation entries.")

    # Load Gemini API Key
    config_path = BASE_DIR / "config" / "api_keys.json"
    if not config_path.exists():
        return "Failed to run self-training: API configuration file keys.json not found."

    try:
        api_keys = json.loads(config_path.read_text(encoding="utf-8"))
        gemini_key = api_keys.get("gemini_api_key")
        if not gemini_key:
            return "Failed to run self-training: gemini_api_key is empty."
    except Exception as e:
        return f"Failed to run self-training: Error reading API keys: {e}"

    print("[Self-Training] Initializing Gemini Client...")
    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
    except Exception as e:
        return f"Failed to run self-training: GenAI client initialization failed: {e}"

    # Current memory status
    current_mem = load_memory()

    prompt = f"""
Analyze the following J.A.R.V.I.S. conversation logs.
Your task is to extract user profile facts, preferences, corrections, project goals, relationships, and plans, and formulate memory updates.

Current Known Memory Context:
{json.dumps(current_mem, indent=2, ensure_ascii=False)}

Conversation Logs:
{chat_corpus}

Extract any NEW information or updates/corrections to current memory.
Return ONLY a valid JSON object in the following format containing the changes to apply (no markdown fences, no explanation):
{{
  "identity": {{ "name": "...", "job": "..." }},
  "preferences": {{ "favorite_color": "...", "language": "..." }},
  "projects": {{ "project_name": "..." }},
  "relationships": {{ "relationship_key": "..." }},
  "wishes": {{ "wish_key": "..." }},
  "notes": {{ "note_key": "..." }}
}}

Only include fields that have updates. If nothing new is found, return an empty JSON object: {{}}
"""

    print("[Self-Training] Sending logs to Gemini for training...")
    try:
        response = None
        last_err = None
        
        # Try gemini-2.5-flash with retries
        for attempt in range(3):
            try:
                print(f"[Self-Training] Attempt {attempt+1} using gemini-2.5-flash...")
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config={"system_instruction": "You are a training agent. Return ONLY valid, minified JSON."}
                )
                break
            except Exception as e:
                last_err = e
                if "503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e) or "demand" in str(e).lower():
                    print(f"[Self-Training] Rate limit/Unavailable. Retrying in 2s...")
                    time.sleep(2)
                else:
                    break
                    
        # If gemini-2.5-flash failed, try gemini-2.0-flash with retries
        if response is None:
            print(f"[Self-Training] gemini-2.5-flash failed ({last_err}), falling back to gemini-2.0-flash...")
            for attempt in range(3):
                try:
                    print(f"[Self-Training] Attempt {attempt+1} using gemini-2.0-flash...")
                    response = client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt,
                        config={"system_instruction": "You are a training agent. Return ONLY valid, minified JSON."}
                    )
                    break
                except Exception as e:
                    last_err = e
                    if "503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e) or "demand" in str(e).lower():
                        print(f"[Self-Training] Rate limit/Unavailable. Retrying in 2s...")
                        time.sleep(2)
                    else:
                        break

        # If gemini-2.0-flash failed, try gemini-flash-latest with retries
        if response is None:
            print(f"[Self-Training] gemini-2.0-flash failed ({last_err}), falling back to gemini-flash-latest...")
            for attempt in range(3):
                try:
                    print(f"[Self-Training] Attempt {attempt+1} using gemini-flash-latest...")
                    response = client.models.generate_content(
                        model="gemini-flash-latest",
                        contents=prompt,
                        config={"system_instruction": "You are a training agent. Return ONLY valid, minified JSON."}
                    )
                    break
                except Exception as e:
                    last_err = e
                    if "503" in str(e) or "429" in str(e) or "UNAVAILABLE" in str(e) or "demand" in str(e).lower():
                        print(f"[Self-Training] Rate limit/Unavailable. Retrying in 2s...")
                        time.sleep(2)
                    else:
                        break
                        
        if response is None:
            raise last_err
            
        clean = (response.text or "").strip()
        clean = re.sub(r"```(?:json)?", "", clean).strip().rstrip("`").strip()
        
        if not clean or clean == "{}":
            return "Self-training complete: No new memory updates or facts detected."

        updates = json.loads(clean)
        if not isinstance(updates, dict) or not updates:
            return "Self-training complete: No new memory updates detected."

        print(f"[Self-Training] Extracted memory updates: {json.dumps(updates)}")
        update_memory(updates)
        
        # Format a nice output message listing the learned facts
        learned = []
        for cat, items in updates.items():
            if isinstance(items, dict):
                for k, v in items.items():
                    val = v.get("value") if isinstance(v, dict) else str(v)
                    learned.append(f"- Learned {cat}/{k}: {val}")
        
        return "Self-training complete!\n" + "\n".join(learned)

    except Exception as e:
        return f"Failed to run self-training: Analysis error: {e}"

if __name__ == "__main__":
    print(run_self_training())
