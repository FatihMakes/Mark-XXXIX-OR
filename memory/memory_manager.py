# memory/memory_manager.py
# Modernized with google-genai SDK (v1.0+) and .env configuration
# Uses unified config loader for API key management

import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock
from uuid import uuid4

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

try:
    from google import genai
except Exception:
    genai = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Import unified config loader
from config.loader import get_base_dir, get_api_key

BASE_DIR = get_base_dir()
MEMORY_DIR = BASE_DIR / "jarvis_memory"
SHORT_TERM_DB_PATH = MEMORY_DIR / "short_term.db"
LONG_TERM_COLLECTION_NAME = "jarvis_long_term"
EMBEDDING_MODEL = "text-embedding-004"


def _get_env_api_key(key_name: str) -> str | None:
    """
    Load API key using unified config loader.
    Priority: .env -> os.environ -> config/api_keys.json
    """
    return get_api_key(key_name)


class JarvisMemory:
    def __init__(self) -> None:
        self.memory_dir = MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        self._db_lock = Lock()
        self._short_term_conn = None
        self._chroma_client = None
        self._chroma_collection = None
        self._genai_client = None
        self._api_key = None

        self._init_short_term_db()
        self._init_genai_client()
        self._init_long_term_store()

    def _init_short_term_db(self) -> None:
        try:
            self._short_term_conn = sqlite3.connect(
                SHORT_TERM_DB_PATH,
                check_same_thread=False,
                isolation_level=None,
            )
            cursor = self._short_term_conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS short_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    role TEXT CHECK(role IN ('user','jarvis')) NOT NULL,
                    content TEXT NOT NULL
                )
                """
            )
            self._short_term_conn.commit()
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to initialize short-term SQLite: {exc}")  # Jarvis: fallback to no short-term store
            self._short_term_conn = None

    def _init_genai_client(self) -> None:
        """
        Initialize the modern google-genai SDK client.
        Replaces deprecated google.generativeai.Client initialization.
        """
        if genai is None:
            self._genai_client = None
            return

        # Get API key from environment (prioritizing .env file)
        self._api_key = _get_env_api_key("GEMINI_API_KEY")
        if not self._api_key:
            self._genai_client = None
            print("[Jarvis Memory] ⚠️ GEMINI_API_KEY not found")  # Jarvis: no API key available
            return

        try:
            # Modern 2026 SDK Client initialization
            self._genai_client = genai.Client(api_key=self._api_key)
            print("[Jarvis Memory] ✅ Google GenAI SDK client initialized")  # Jarvis: Gemini SDK ready
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to initialize Gemini client: {exc}")  # Jarvis: embedding service unavailable
            self._genai_client = None

    def _embed_text(self, text: str) -> list[float] | None:
        """
        Generate embeddings using the modern google-genai SDK.
        Uses text-embedding-004 model with updated API format.
        """
        if self._genai_client is None:
            return None

        cleaned_text = (text or "").strip()
        if not cleaned_text:
            return None

        try:
            # Modern 2026 API format for text embeddings
            # Pass text directly as string
            response = self._genai_client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=cleaned_text,
            )

            # Handle response - check for different attribute names
            # Try embeddings first (list format)
            if hasattr(response, "embeddings") and response.embeddings:
                embedding = response.embeddings
                # Handle list of embeddings
                if isinstance(embedding, list) and len(embedding) > 0:
                    first_embedding = embedding[0]
                    if hasattr(first_embedding, "values"):
                        return first_embedding.values
                    if hasattr(first_embedding, "embedding"):
                        return first_embedding.embedding
                    if isinstance(first_embedding, (list, tuple)):
                        return list(first_embedding)

            # Try embedding attribute (single embedding format)
            if hasattr(response, "embedding"):
                embedding = response.embedding
                if hasattr(embedding, "values"):
                    return embedding.values
                if hasattr(embedding, "embedding"):
                    return embedding.embedding
                if isinstance(embedding, (list, tuple)):
                    return list(embedding)

            # Handle dict-like response
            if hasattr(response, "__dict__"):
                for attr_name in ["embeddings", "embedding"]:
                    attr = getattr(response, attr_name, None)
                    if attr is not None:
                        if isinstance(attr, list) and len(attr) > 0:
                            item = attr[0]
                            if hasattr(item, "values"):
                                return list(item.values)
                            if hasattr(item, "embedding"):
                                return list(item.embedding)
                            if isinstance(item, (list, tuple)):
                                return list(item)

            print("[Jarvis Memory] ⚠️ Failed to extract embedding from response")  # Jarvis: embedding extraction failed
            return None

        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to create embedding: {exc}")  # Jarvis: embedding service unavailable
            return None

    def _create_chroma_client(self):
        if chromadb is None:
            raise ImportError("chromadb is not installed")

        if hasattr(chromadb, "PersistentClient"):
            return chromadb.PersistentClient(path=str(self.memory_dir))

        if hasattr(chromadb, "Client") and Settings is not None:
            return chromadb.Client(Settings(persist_directory=str(self.memory_dir), chroma_db_impl="duckdb+parquet"))

        raise RuntimeError("Unsupported chromadb client API")

    def _init_long_term_store(self) -> None:
        try:
            if chromadb is None:
                raise ImportError("chromadb is not installed")

            self._chroma_client = self._create_chroma_client()
            self._chroma_collection = self._chroma_client.get_or_create_collection(
                name=LONG_TERM_COLLECTION_NAME,
            )
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to initialize long-term ChromaDB: {exc}")  # Jarvis: long-term recall is disabled
            self._chroma_client = None
            self._chroma_collection = None

    def save_interaction(self, role: str, content: str) -> bool:
        if self._short_term_conn is None:
            return False

        role = role if role in {"user", "jarvis"} else "user"
        text = (content or "").strip()
        if not text:
            return False

        try:
            with self._db_lock:
                cursor = self._short_term_conn.cursor()
                cursor.execute(
                    "INSERT INTO short_term_memory (role, content) VALUES (?, ?)",
                    (role, text),
                )
                self._short_term_conn.commit()
            return True
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to save short-term interaction: {exc}")  # Jarvis: short-term memory write failed
            return False

    def get_recent_context(self, limit: int = 5) -> list[dict]:
        if self._short_term_conn is None:
            return []

        try:
            cursor = self._short_term_conn.cursor()
            cursor.execute(
                "SELECT id, timestamp, role, content FROM short_term_memory ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            rows = cursor.fetchall()
            context = [
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "role": row[2],
                    "content": row[3],
                }
                for row in rows
            ]
            return list(reversed(context))
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to read short-term context: {exc}")  # Jarvis: read failed, but I can continue
            return []

    def clear_short_term(self) -> None:
        if self._short_term_conn is None:
            return

        try:
            with self._db_lock:
                cursor = self._short_term_conn.cursor()
                cursor.execute("DELETE FROM short_term_memory")
                self._short_term_conn.commit()
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to clear short-term memory: {exc}")  # Jarvis: cleanup failed

    def store_permanent_fact(self, fact_text: str, metadata: dict | None = None) -> list[str]:
        if self._chroma_collection is None or self._genai_client is None:
            return []

        text = (fact_text or "").strip()
        if not text:
            return []

        try:
            embedding = self._embed_text(text)
            if not embedding:
                print("[Jarvis Memory] ⚠️ Failed to get embedding for permanent fact.")  # Jarvis: long-term store failed
                return []

            item_id = str(uuid4())
            self._chroma_collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[item_id],
                embeddings=[embedding],
            )
            return [item_id]
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to store permanent fact: {exc}")  # Jarvis: long-term store failed
            return []

    def recall_relevant_facts(self, query_text: str, n_results: int = 3) -> list[dict]:
        if self._chroma_collection is None or self._genai_client is None:
            return []

        query = (query_text or "").strip()
        if not query:
            return []

        try:
            embedding = self._embed_text(query)
            if not embedding:
                print("[Jarvis Memory] ⚠️ Failed to get embedding for query.")  # Jarvis: semantic recall failed
                return []

            results = self._chroma_collection.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]

            facts = []
            for content, metadata, distance in zip(documents, metadatas, distances):
                facts.append(
                    {
                        "content": content,
                        "metadata": metadata or {},
                        "distance": distance,
                    }
                )
            return facts
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to recall long-term facts: {exc}")  # Jarvis: semantic recall failed
            return []

    def load_memory(self) -> dict:
        if self._chroma_collection is None:
            return {"facts": []}

        try:
            data = self._chroma_collection.get(include=["documents", "metadatas"])
            documents = data.get("documents", [])
            metadatas = data.get("metadatas", [])

            if documents and isinstance(documents[0], list):
                documents = documents[0]
            if metadatas and isinstance(metadatas[0], list):
                metadatas = metadatas[0]

            facts = [
                {"content": doc, "metadata": metadata or {}}
                for doc, metadata in zip(documents, metadatas)
                if isinstance(doc, str) and doc.strip()
            ]
            return {"facts": facts}
        except Exception as exc:
            print(f"[Jarvis Memory] ⚠️ Failed to load memory facts: {exc}")  # Jarvis: loading memories failed
            return {"facts": []}

    def update_memory(self, memory_update: dict) -> dict:
        if not isinstance(memory_update, dict) or not memory_update:
            return self.load_memory()

        facts = self._serialize_memory_update(memory_update)
        for fact_text, metadata in facts:
            self.store_permanent_fact(fact_text, metadata)

        return self.load_memory()

    @staticmethod
    def _serialize_memory_update(memory_update: dict) -> list[tuple[str, dict]]:
        facts: list[tuple[str, dict]] = []
        for category, entries in memory_update.items():
            if not isinstance(entries, dict):
                continue
            for key, entry in entries.items():
                if isinstance(entry, dict) and "value" in entry:
                    value = entry["value"]
                else:
                    value = entry

                if value is None:
                    continue
                value_text = str(value).strip()
                if not value_text:
                    continue

                key_text = str(key).strip()
                category_text = str(category).strip()
                fact_text = (
                    f"{category_text}.{key_text}: {value_text}"
                    if category_text and key_text
                    else f"{key_text}: {value_text}"
                )

                facts.append(
                    (
                        fact_text,
                        {
                            "category": category_text,
                            "key": key_text,
                        },
                    )
                )
        return facts


jarvis_memory = JarvisMemory()


def save_interaction(role: str, content: str) -> bool:
    return jarvis_memory.save_interaction(role, content)


def get_recent_context(limit: int = 5) -> list[dict]:
    return jarvis_memory.get_recent_context(limit)


def clear_short_term() -> None:
    jarvis_memory.clear_short_term()


def store_permanent_fact(fact_text: str, metadata: dict | None = None) -> list[str]:
    return jarvis_memory.store_permanent_fact(fact_text, metadata)


def recall_relevant_facts(query_text: str, n_results: int = 3) -> list[dict]:
    return jarvis_memory.recall_relevant_facts(query_text, n_results)


def load_memory() -> dict:
    return jarvis_memory.load_memory()


def update_memory(memory_update: dict) -> dict:
    return jarvis_memory.update_memory(memory_update)


def format_memory_for_prompt(memory: dict | None) -> str:
    if not memory:
        return ""

    if "facts" in memory:
        facts = memory.get("facts", [])
        if not facts:
            return ""

        lines = ["[LONG-TERM MEMORY — use naturally, never recite like a list]"]
        for fact in facts[:10]:
            content = str(fact.get("content", "")).strip()
            if not content:
                continue
            metadata = fact.get("metadata") or {}
            metadata_text = ""
            if metadata:
                metadata_pairs = [f"{k}={v}" for k, v in metadata.items() if v is not None]
                if metadata_pairs:
                    metadata_text = f" ({', '.join(metadata_pairs)})"
            lines.append(f"- {content}{metadata_text}")

        return "\n".join(lines) + "\n"

    # Legacy fallback for older category-based memory shape
    legacy_fields = ["identity", "preferences", "projects", "relationships", "wishes", "notes"]
    if any(isinstance(memory.get(field), dict) for field in legacy_fields):
        lines = []

        identity = memory.get("identity", {})
        if isinstance(identity, dict):
            id_fields = ["name", "age", "birthday", "city", "job", "language", "school", "nationality"]
            for field in id_fields:
                entry = identity.get(field)
                if entry:
                    val = entry.get("value") if isinstance(entry, dict) else entry
                    if val:
                        lines.append(f"{field.title()}: {val}")
            for key, entry in identity.items():
                if key in id_fields:
                    continue
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"{key.replace('_', ' ').title()}: {val}")

        prefs = memory.get("preferences", {})
        if isinstance(prefs, dict) and prefs:
            lines.append("")
            lines.append("Preferences:")
            for key, entry in list(prefs.items())[:15]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        projects = memory.get("projects", {})
        if isinstance(projects, dict) and projects:
            lines.append("")
            lines.append("Active Projects / Goals:")
            for key, entry in list(projects.items())[:8]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        rels = memory.get("relationships", {})
        if isinstance(rels, dict) and rels:
            lines.append("")
            lines.append("People in their life:")
            for key, entry in list(rels.items())[:10]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        wishes = memory.get("wishes", {})
        if isinstance(wishes, dict) and wishes:
            lines.append("")
            lines.append("Wishes / Plans / Wants:")
            for key, entry in list(wishes.items())[:8]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

        notes = memory.get("notes", {})
        if isinstance(notes, dict) and notes:
            lines.append("")
            lines.append("Other notes:")
            for key, entry in list(notes.items())[:8]:
                val = entry.get("value") if isinstance(entry, dict) else entry
                if val:
                    lines.append(f"  - {key}: {val}")

        if not lines:
            return ""

        header = "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]\n"
        result = header + "\n".join(lines)
        if len(result) > 2000:
            result = result[:1997] + "…"
        return result + "\n"

    return ""


def should_extract_memory(user_text: str, jarvis_text: str, api_key: str = "") -> bool:
    try:
        from or_client import client

        combined = f"User: {user_text[:300]}\nJarvis: {jarvis_text[:1000]}"

        result = client.chat(
            f"Does this conversation contain ANY of the following?\n"
            f"- Personal facts (name, age, city, job, birthday, nationality)\n"
            f"- Preferences or favorites (food, color, music, sport, game, film, book, etc.)\n"
            f"- Active projects or goals the user is working on\n"
            f"- People in the user's life (friends, family, partner, colleagues)\n"
            f"- Things the user wants to do or buy in the future\n"
            f"- Any other fact worth remembering long-term\n\n"
            f"Reply only YES or NO.\n\nConversation:\n{combined}",
            system="You are a memory relevance checker. Reply only YES or NO.",
            max_tokens=5,
            temperature=0.0,
        )
        return "YES" in result.upper()

    except Exception as exc:
        print(f"[Jarvis Memory] ⚠️ Stage1 check failed: {exc}")  # Jarvis: memory relevance detection failed
        return False


def extract_memory(user_text: str, jarvis_text: str, api_key: str = "") -> dict:
    try:
        from or_client import client

        combined = f"User: {user_text[:600]}\nJarvis: {jarvis_text[:300]}"

        raw = client.chat(
            f"Extract ALL memorable personal facts from this conversation. Any language.\n"
            f"Return ONLY valid JSON. Use {{}} if truly nothing is worth saving.\n\n"
            f"Category guide:\n"
            f"  identity      → name, age, birthday, city, country, job, school, nationality, language\n"
            f"  preferences   → ANY favorite or preferred thing:\n"
            f"                  favorite_food, favorite_color, favorite_music, favorite_film,\n"
            f"                  favorite_game, favorite_sport, favorite_book, favorite_artist,\n"
            f"                  favorite_country, hobbies, interests, dislikes, etc.\n"
            f"  projects      → projects being built, ongoing work, goals, ideas in progress\n"
            f"                  (e.g. mark_xxv: 'Building a JARVIS-like AI assistant')\n"
            f"  relationships → people mentioned: friends, family, partner, colleagues\n"
            f"                  (e.g. best_friend_ali: 'Best friend, met in university')\n"
            f"  wishes        → future plans, things to buy, travel plans, dreams\n"
            f"  notes         → anything else worth remembering (habits, schedule, etc.)\n\n"
            f"IMPORTANT:\n"
            f"- Be LIBERAL: if something MIGHT be worth remembering, include it.\n"
            f"- Extract from BOTH user and Jarvis turns.\n"
            f"- Skip: weather, reminders, search results, one-time commands.\n"
            f"- Use concise English values regardless of conversation language.\n\n"
            f"Format:\n"
            f'{{"identity":{{"name":{{"value":"Ali"}}}},\n'
            f' "preferences":{{"favorite_color":{{"value":"blue"}}}},\n'
            f' "projects":{{"mark_xxv":{{"value":"JARVIS-like AI assistant"}}}},\n'
            f' "relationships":{{"friend_yusuf":{{"value":"close friend"}}}},\n'
            f' "wishes":{{"buy_guitar":{{"value":"wants an acoustic guitar"}}}},\n'
            f' "notes":{{"works_at_night":{{"value":"usually active late at night"}}}}}}\n\n'
            f"Conversation:\n{combined}\n\nJSON:",
            system="Return ONLY valid JSON. No markdown, no explanation, no extra text.",
            max_tokens=1024,
            temperature=0.2,
        )

        clean = raw.strip()
        clean = re.sub(r"```(?:json)?", "", clean).strip().rstrip("`").strip()

        if not clean or clean == "{}":
            return {}

        return json.loads(clean)

    except json.JSONDecodeError:
        return {}
    except Exception as exc:
        if "429" not in str(exc):
            print(f"[Jarvis Memory] ⚠️ Extract failed: {exc}")  # Jarvis: extraction failed
        return {}
