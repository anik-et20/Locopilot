import json
import os
from pathlib import Path
from typing import List, Dict, Any

# Path to the chat history file
HISTORY_FILE = Path("logs/chat_history.json")

class ChatHistoryManager:
    def __init__(self):
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        if not HISTORY_FILE.parent.exists():
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not HISTORY_FILE.exists():
            self._write_file([])

    def _read_file(self) -> List[Dict[str, str]]:
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_file(self, data: List[Dict[str, str]]):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_all(self) -> List[Dict[str, str]]:
        """Retrieve the entire chat history."""
        return self._read_file()

    def add_message(self, role: str, content: str):
        """Append a single message to the chat history."""
        history = self._read_file()
        history.append({"role": role, "content": content})
        self._write_file(history)

    def clear_all(self):
        """Wipe the chat history."""
        self._write_file([])

chat_history_db = ChatHistoryManager()
