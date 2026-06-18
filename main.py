import asyncio
import threading
import json
import sys
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
import traceback
import time
from pathlib import Path

import sounddevice as sd
from google import genai
from google.genai import types
from ui import JarvisUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    should_extract_memory, extract_memory, save_chat_history
)

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.cmd_control       import cmd_control
from actions.world_monitor      import world_monitor


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-latest"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024

force_offline = False
last_offline_time = 0.0


def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are JARVIS, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )
    
_last_memory_input = ""

def _update_memory_async(user_text: str, jarvis_text: str) -> None:
    global _last_memory_input

    user_text   = (user_text   or "").strip()
    jarvis_text = (jarvis_text or "").strip()

    if len(user_text) < 5 or user_text == _last_memory_input:
        return
    _last_memory_input = user_text

    try:
        api_key = _get_api_key()
        if not should_extract_memory(user_text, jarvis_text, api_key):
            return
        data = extract_memory(user_text, jarvis_text, api_key)
        if data:
            update_memory(data)
            print(f"[Memory] [Success] {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] [Warning] {e}")

TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the Windows computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "world_monitor",
        "description": (
            "Real-time global intelligence brief from 60+ curated live news feeds "
            "(geopolitics, regions, finance, defense). Use whenever the user asks what's "
            "happening in the world / a region, latest news, world situation, market or "
            "defense developments, or to update the World Monitor dashboard."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": "One of: world, us, europe, middleeast, asia, africa, latam, tech, ai, finance, energy, defense, crisis. Default 'world'."
                },
                "brief": {
                    "type": "BOOLEAN",
                    "description": "True (default) = spoken AI-synthesized brief. False = raw headline list."
                }
            },
            "required": []
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Windows Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls the web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, any web-based task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
    "name": "shutdown_jarvis",
    "description": (
        "Shuts down the assistant completely. "
        "Call this when the user expresses intent to end the conversation, "
        "close the assistant, say goodbye, or stop Jarvis. "
        "The user can say this in ANY language."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {},
    }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "cmd_control",
        "description": (
            "Executes commands in CMD or PowerShell on the Windows system. "
            "Use this for: running git pull/clone, pip/npm installs, running custom python/node scripts, "
            "running batch files, managing files, checking process states, or any system execution."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "The command line string to run."
                }
            },
            "required": ["command"]
        }
    },
    {
        "name": "moltbot_control",
        "description": "Controls moltbot: query health, open control center dashboard, or run onboarding daemon.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "health | dashboard | onboard"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "self_training",
        "description": "Trains J.A.R.V.I.S. by reading past chat history from MongoDB, extracting your profile, habits, preferences, and corrections, and saving them to long term memory registry.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "limit": {
                    "type": "INTEGER",
                    "description": "Number of recent chat logs to analyze (default is 100)."
                }
            }
        }
    },
    {
        "name": "github_updater",
        "description": "Clones a specified GitHub repository to a scratch folder, studies its documentation and python scripts, and writes a features study report artifact so J.A.R.V.I.S. can write actions to update himself.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_url": {
                    "type": "STRING",
                    "description": "The URL of the GitHub repository to study and update from (e.g. https://github.com/username/repo)."
                }
            },
            "required": ["repo_url"]
        }
    },
    {
        "name": "self_upgrade",
        "description": (
            "Build a NEW skill/capability for yourself. Given a capability description "
            "(and optionally a GitHub repo URL for reference), you generate a new Python "
            "skill, it is compile-checked and installed, and becomes a usable tool after a "
            "restart. Use when the user asks you to learn/add a new ability or integrate a repo."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "capability": {"type": "STRING", "description": "Plain description of the new ability to build."},
                "repo_url":   {"type": "STRING", "description": "Optional GitHub repo URL to learn from."},
                "name":       {"type": "STRING", "description": "Optional short name for the skill."}
            },
            "required": []
        }
    },
]

# --- Dynamic self-extending skills: auto-load anything in skills/ as a tool ---
try:
    from skills.loader import load_skills
    _SKILL_DECLS, _SKILL_DISPATCH = load_skills()
    if _SKILL_DECLS:
        TOOL_DECLARATIONS.extend(_SKILL_DECLS)
    print(f"[Skills] Loaded {len(_SKILL_DISPATCH)} dynamic skill(s): {list(_SKILL_DISPATCH)}")
except Exception as e:
    _SKILL_DECLS, _SKILL_DISPATCH = [], {}
    print(f"[Skills] Loader error: {e}")


class JarvisLive:

    def __init__(self, ui: JarvisUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_complete_received = False
        self._session_handle = None   # for seamless session resumption across reconnects
        self._last_speak_end = 0.0    # timestamp speech last ended (mic echo cooldown)
        self.ECHO_COOLDOWN = 0.4      # seconds to keep mic gated after Jarvis stops talking

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
            if not value:
                # Record when speech ended so the mic can stay gated through the
                # speaker buffer's tail (prevents Jarvis's own echo from triggering
                # a false "interrupt" that cuts the next reply mid-sentence).
                self._last_speak_end = time.time()
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        num_notes = len(memory.get('notes', {}))
        self.ui.write_log(f"MEMORY: Loaded context ({num_notes} facts loaded from local DB).")
        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
            # Keep the session alive indefinitely: compress old context instead of
            # letting the server hit its window cap and close the socket mid-sentence.
            context_window_compression=types.ContextWindowCompressionConfig(
                sliding_window=types.SlidingWindow()
            ),
            # Let us resume the SAME session after a server-side drop so the voice
            # continues seamlessly instead of cold-restarting (the "awaz atakti hai" bug).
            session_resumption=types.SessionResumptionConfig(handle=self._session_handle),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[JARVIS] [Tool Call] {name}  {args}")
        self.ui.set_state("EXECUTING")
        self.ui.set_tool_state(name, "active")
        self.ui.write_timeline(f"Tool running: {name} (Params: {json.dumps(args)})")
        self.ui.update_intent("", f"Executing Tool: {name}")
        
        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] [Sync] save_memory: {category}/{key} = {value}")
                self.ui.write_log(f"MEMORY: Saved to {category}/{key} -> {value}")
            self.ui.set_tool_state(name, "idle")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."
        
        self.ui.write_log(f"TOOL: Running '{name}' with params: {json.dumps(args)}")

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."


            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "cmd_control":
                r = await loop.run_in_executor(None, lambda: cmd_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "world_monitor":
                r = await loop.run_in_executor(None, lambda: world_monitor(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "moltbot_control":
                action = args.get("action", "health").lower()
                cmd = f"clawdbot {action}"
                r = await loop.run_in_executor(None, lambda: cmd_control(parameters={"command": cmd}, player=self.ui))
                result = r or "Done."
            elif name == "self_training":
                limit = args.get("limit", 100)
                from actions.self_training import run_self_training
                r = await loop.run_in_executor(None, lambda: run_self_training(limit=limit))
                result = r or "Done."
            elif name == "github_updater":
                repo_url = args.get("repo_url", "")
                from actions.github_updater import run_github_updater
                r = await loop.run_in_executor(None, lambda: run_github_updater(repo_url=repo_url))
                result = r or "Done."
            elif name == "self_upgrade":
                from actions.self_upgrade import run_self_upgrade
                r = await loop.run_in_executor(None, lambda: run_self_upgrade(
                    capability=args.get("capability", ""),
                    repo_url=args.get("repo_url", ""),
                    name=args.get("name", "")))
                result = r or "Done."
            elif name in _SKILL_DISPATCH:
                fn = _SKILL_DISPATCH[name]
                r = await loop.run_in_executor(None, lambda: fn(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."
            elif name == "shutdown_jarvis":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")

                def _shutdown():
                    import time, sys, os
                    time.sleep(1)
                    os._exit(0)

                threading.Thread(target=_shutdown, daemon=True).start()
            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)
            self.ui.set_tool_state(name, "failed")
            self.ui.write_log(f"ERR: Tool '{name}' failed: {e}")
            self.ui.write_timeline(f"Tool failed: {name} - {str(e)[:60]}")
            self.ui.update_intent("", f"Failed Tool: {name}")
        else:
            self.ui.set_tool_state(name, "idle")
            self.ui.write_log(f"TOOL: Finished '{name}' successfully.")
            self.ui.write_timeline(f"Tool success: {name}")
            self.ui.update_intent("", f"Finished Tool: {name}")

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[JARVIS] [Tool Output] {name} -> {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        print("[JARVIS] [Mic] Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            # Stay gated during speech AND for a short cooldown after, so the
            # speaker's audio tail / room echo can't trigger a false interruption.
            in_cooldown = (time.time() - self._last_speak_end) < self.ECHO_COOLDOWN
            if not jarvis_speaking and not in_cooldown and not self.ui.muted:
                data = indata.tobytes()
                loop.call_soon_threadsafe(
                    self.out_queue.put_nowait,
                    {"data": data, "mime_type": "audio/pcm;rate=16000"}
                )

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[JARVIS] [Mic] Mic stream open")
                while True:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[JARVIS] [Error] Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[JARVIS] [Receiver] Receiver started")
        out_buf, in_buf = [], []
        thinking_started = False

        try:
            async for response in self.session.receive():

                    # Save the resumption handle so a reconnect continues this same session.
                    if getattr(response, "session_resumption_update", None):
                        upd = response.session_resumption_update
                        if upd.resumable and upd.new_handle:
                            self._session_handle = upd.new_handle

                    # Server is about to close this socket; the handle above lets us
                    # reconnect seamlessly. Just log it — don't treat as a hard failure.
                    if getattr(response, "go_away", None):
                        print(f"[JARVIS] [Connection] Server go_away (time_left={response.go_away.time_left}); will resume session.")

                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                self.audio_in_queue.put_nowait(part.inline_data.data)

                    if response.server_content:
                        sc = response.server_content
                        if sc.interrupted:
                            print("[JARVIS] Model interrupted by user.")
                            while not self.audio_in_queue.empty():
                                try:
                                    self.audio_in_queue.get_nowait()
                                except asyncio.QueueEmpty:
                                    break
                            self.set_speaking(False)
                            self._turn_complete_received = False

                        # Stream thinking parts to UI
                        if sc.model_turn and sc.model_turn.parts:
                            for part in sc.model_turn.parts:
                                if getattr(part, 'thought', False) and part.text:
                                    if not thinking_started:
                                        self.ui.write_timeline("Thought: Cognitive reasoning started...")
                                        thinking_started = True
                                    self.ui.write_thought(part.text)

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            txt = sc.output_transcription.text.strip()
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text.strip()
                            if txt:
                                in_buf.append(txt)
                                self.ui.update_intent(txt, "Transcribing...")

                        if sc.turn_complete:
                            self._turn_complete_received = True
                            if self.audio_in_queue.empty() and not self._is_speaking:
                                self.set_speaking(False)
                                self._turn_complete_received = False

                            thinking_started = False
                            full_in = " ".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                                self.ui.update_intent(full_in, "Reasoning...")
                                self.ui.write_timeline(f"You: {full_in}")
                                self.ui.clear_thoughts()
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Jarvis: {full_out}")
                                self.ui.write_timeline(f"Jarvis: {full_out}")
                            out_buf = []

                            if full_in or full_out:
                                threading.Thread(
                                    target=save_chat_history,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                            if full_in and len(full_in) > 5:
                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[JARVIS] [Tool Request] {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )
            
            # If receive completes without error, it means the connection closed
            raise ConnectionError("Live connection closed by server")

        except Exception as e:
            print(f"[JARVIS] [Error] Recv: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        print("[JARVIS] [Speaker] Speaker playback started")
        loop = asyncio.get_event_loop()

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=0,        # let PortAudio choose — avoids tiny-block underruns
            latency="high",     # larger output buffer absorbs network jitter -> no mid-word gaps
        )
        stream.start()
        try:
            while True:
                chunk = await self.audio_in_queue.get()
                if not self._is_speaking:
                    self.set_speaking(True)
                # Coalesce all immediately-available chunks into one larger write so the
                # device buffer never starves between many small writes (the "halka atak").
                buf = bytearray(chunk)
                while not self.audio_in_queue.empty():
                    try:
                        buf += self.audio_in_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                await asyncio.to_thread(stream.write, bytes(buf))
                # Only stop speaking once the turn is done AND the buffer is drained.
                if self._turn_complete_received and self.audio_in_queue.empty():
                    self.set_speaking(False)
                    self._turn_complete_received = False
        except Exception as e:
            if "cannot schedule new futures" in str(e):
                pass
            else:
                print(f"[JARVIS] [Error] Play: {e}")
                raise
        finally:
            self.set_speaking(False)
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        consecutive_failures = 0

        while True:
            try:
                print("[JARVIS] [Connection] Connecting...")
                self.ui.set_state("THINKING")
                self.ui.write_log("THOUGHT: Initializing session & connecting to neural core...")
                self.ui.write_timeline("Connecting to neural core...")
                config = self._build_config()

                t_start = time.time()
                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    self.out_queue      = asyncio.Queue()

                    print("[JARVIS] [Connection] Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: JARVIS online.")
                    self.ui.write_timeline("Neural link online. JARVIS is ready.")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    
            except BaseException as e:
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                print(f"[JARVIS] [Warning] Connection exception: {e}")
                traceback.print_exc()

                # A clean, resumable drop is NOT a failure: we have a handle and will
                # continue the same session on reconnect. Reset the counter so seamless
                # resumes never trip the offline fallback.
                is_policy_error = "1008" in str(e) or "policy violation" in str(e).lower() or "not implemented" in str(e).lower()
                if self._session_handle and not is_policy_error and check_internet():
                    consecutive_failures = 0
                elif time.time() - t_start < 300 or is_policy_error:
                    # Quick failure / policy / quota error before any working session.
                    consecutive_failures += 1
                else:
                    consecutive_failures = 1

                print(f"[JARVIS] DEBUG: consecutive_failures={consecutive_failures}, duration={time.time() - t_start:.2f}s, is_policy_error={is_policy_error}")
                self.ui.write_log(f"ERR: Neural link disconnected. Attempt {consecutive_failures} failed.")
                self.ui.write_timeline(f"Neural link disconnected (Attempt {consecutive_failures}/2).")
                
                # If internet connection is lost, too many attempts fail, or it's a policy error, fall back to offline core
                if not check_internet() or consecutive_failures >= 2 or is_policy_error:
                    print("[JARVIS] Falling back to offline core.")
                    global force_offline, last_offline_time
                    force_offline = True
                    last_offline_time = time.time()
                    break

            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[JARVIS] [Connection] Reconnecting in 3s...")
            await asyncio.sleep(3)

def check_internet() -> bool:
    import socket
    try:
        socket.setdefaulttimeout(1.5)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect(("8.8.8.8", 53))
        return True
    except Exception:
        return False


class JarvisOffline:
    def __init__(self, ui: JarvisUI):
        self.ui = ui
        self.ui.on_text_command = self._on_text_command
        self.running = True
        self.whisper = None
        self.speaker = None
        self.is_speaking = False
        self.last_speak_end_time = 0.0
        
        # Load local memory context
        try:
            memory = load_memory()
            mem_str = format_memory_for_prompt(memory)
        except Exception as e:
            print(f"[Offline Memory Error] {e}")
            mem_str = ""

        # Initialize history
        sys_prompt = (
            "You are JARVIS, Tony Stark's AI assistant, currently running in local OFFLINE MODE. "
            "Be extremely brief and direct. Speak as JARVIS. "
            "You do not have access to live internet search or external tools right now. "
            "Keep your responses concise and ready for spoken delivery.\n\n"
        )
        if mem_str:
            sys_prompt += mem_str

        self.history = [{"role": "system", "content": sys_prompt}]

    def _on_text_command(self, text: str):
        threading.Thread(target=self.process_query, args=(text,), daemon=True).start()

    def speak(self, text: str):
        self.is_speaking = True
        self.ui.write_log(f"Jarvis: {text}")
        self.ui.write_timeline(f"Jarvis: {text}")
        self.ui.start_speaking()
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Speak(text)
        except Exception as e:
            print(f"[Offline TTS Error] {e}")
        finally:
            import time
            self.ui.stop_speaking()
            self.last_speak_end_time = time.time()
            self.is_speaking = False

    def query_local_llm(self, text: str) -> str:
        import requests
        
        # 1. Try Ollama (OpenAI compatible chat completions endpoint)
        try:
            url = "http://localhost:11434/v1/chat/completions"
            payload = {
                "model": "qwen2.5:1.5b",
                "messages": self.history + [{"role": "user", "content": text}],
                "temperature": 0.7
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                return res.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

        # 2. Try Odysseus chat endpoint
        try:
            url = "http://localhost:7000/api/chat"
            payload = {
                "message": text
            }
            res = requests.post(url, json=payload, timeout=8)
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, dict):
                    return data.get("response", str(data))
                return res.text
        except Exception:
            pass

        return "I am currently offline, and I could not connect to local AI models. Please ensure Ollama or Odysseus is running."

    def process_query(self, text: str):
        self.ui.write_log(f"You: {text}")
        self.ui.write_timeline(f"You: {text}")
        self.ui.update_intent(text, "Local Reasoning...")
        self.ui.set_state("OFFLINE_THINKING")

        # Basic offline matched actions
        lower_text = text.lower()
        matched_app = None
        if "open" in lower_text:
            for app in ["chrome", "notepad", "calculator", "spotify", "discord", "cmd", "explorer"]:
                if app in lower_text:
                    matched_app = app
                    break
                    
        if matched_app:
            self.ui.write_log(f"TOOL: Offline command matched, opening {matched_app}")
            try:
                from actions.open_app import open_app
                open_app(parameters={"app_name": matched_app}, response=None, player=self.ui)
                reply = f"Opening {matched_app}, sir."
            except Exception as e:
                reply = f"I tried to open {matched_app}, but encountered an error: {e}"
        else:
            # Query local LLM
            reply = self.query_local_llm(text)

        self.ui.clear_thoughts()
        self.ui.write_timeline("Local thought finished.")

        # Update history
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply})
        if len(self.history) > 15:
            self.history = [self.history[0]] + self.history[-12:]

        self.speak(reply)

    def run(self):
        import speech_recognition as sr
        import numpy as np
        import win32com.client
        from faster_whisper import WhisperModel
        import time

        self.ui.write_log("SYS: Initializing local AI components...")
        self.ui.set_state("OFFLINE_THINKING")

        # Initialize TTS
        try:
            self.speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self.ui.write_log("SYS: local SAPI5 Text-to-Speech initialized.")
        except Exception as e:
            self.ui.write_log(f"ERR: SAPI5 TTS failed: {e}")

        # Initialize faster-whisper
        try:
            self.ui.write_log("SYS: Loading faster-whisper model...")
            self.whisper = WhisperModel("base", device="cpu", compute_type="int8")
            self.ui.write_log("SYS: Local Speech-to-Text model loaded.")
        except Exception as e:
            self.ui.write_log(f"ERR: Speech-to-Text init failed: {e}")

        recognizer = sr.Recognizer()
        microphone = sr.Microphone()

        try:
            with microphone as source:
                self.ui.write_log("SYS: Calibrating microphone for ambient noise...")
                recognizer.adjust_for_ambient_noise(source, duration=1.5)
                self.ui.write_log("SYS: Calibration complete.")
        except Exception as e:
            self.ui.write_log(f"ERR: Mic calibration failed: {e}")

        self.ui.set_state("OFFLINE_LISTENING")
        self.ui.write_log("SYS: JARVIS offline core ready.")
        self.ui.write_timeline("Offline mode active. Standing by.")

        # Main offline listen loop
        while self.running:
            # Check if cooling down period over
            global force_offline, last_offline_time
            if force_offline and (time.time() - last_offline_time > 3600):
                print("[JARVIS] Offline cooling-down period over. Enabling online retry.")
                force_offline = False

            # Check if internet restored
            if check_internet() and not force_offline:
                self.ui.write_log("SYS: Internet connection restored. Returning online.")
                self.ui.write_timeline("Internet connection restored. Switching to Online Mode.")
                break

            if self.ui.muted:
                time.sleep(0.5)
                continue

            # If SAPI5 is currently speaking, wait until it completes before listening
            while self.is_speaking:
                time.sleep(0.2)

            try:
                self.ui.set_state("OFFLINE_LISTENING")
                with microphone as source:
                    audio = recognizer.listen(source, timeout=3.0, phrase_time_limit=10.0)

                if self.ui.muted:
                    continue

                # Discard audio recorded during or immediately after SAPI5 speaks
                if time.time() - self.last_speak_end_time < 1.5:
                    print("[Offline Mic] Discarded speech input overlap with SAPI5 voice output.")
                    continue

                self.ui.set_state("OFFLINE_THINKING")
                self.ui.write_timeline("Transcribing local speech...")

                raw_data = audio.get_raw_data(convert_rate=16000, convert_width=2)
                audio_np = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0

                if self.whisper:
                    segments, _ = self.whisper.transcribe(audio_np, beam_size=3, vad_filter=True)
                    text = " ".join(s.text for s in segments).strip()
                    if text:
                        self.process_query(text)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                print(f"[Offline Loop Error] {e}")
                time.sleep(0.5)


def main():
    ui = JarvisUI("face.png")

    def runner():
        global force_offline, last_offline_time
        import time
        ui.wait_for_api_key()
        while True:
            # Check if cooling down period is over
            if force_offline and (time.time() - last_offline_time > 3600):
                print("[JARVIS] Offline cooling-down period over. Retrying online connection...")
                force_offline = False

            if check_internet() and not force_offline:
                print("[JARVIS] Internet connection detected. Running in Online Mode.")
                jarvis = JarvisLive(ui)
                try:
                    asyncio.run(jarvis.run())
                except Exception as e:
                    print(f"[JARVIS] Online loop stopped: {e}")
            else:
                print("[JARVIS] Running in Offline Mode.")
                jarvis_offline = JarvisOffline(ui)
                try:
                    jarvis_offline.run()
                except Exception as e:
                    print(f"[JARVIS] Offline loop stopped: {e}")
            time.sleep(3)

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()


if __name__ == "__main__":
    main()