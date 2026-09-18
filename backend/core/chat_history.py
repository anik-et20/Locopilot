"""
Session-Aware Chat History Database
Persists chat conversations grouped by unique session IDs under settings.logs_dir / "chat_sessions".
Dynamically resolves paths from central settings with zero hardcoded relative path assumptions.
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import settings

class ChatHistoryManager:
    def __init__(self):
        self.sessions_dir = settings.logs_dir / "chat_sessions"
        self._ensure_storage()

    def _ensure_storage(self):
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        # Sanitize session_id to prevent any directory escape
        safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_") or "default"
        return self.sessions_dir / f"{safe_id}.json"

    def get_session_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Load messages for a specific session."""
        fpath = self._session_file(session_id)
        if not fpath.exists():
            return []
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", [])
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def add_message(self, session_id: Optional[str], role: str, content: str):
        """Append a message to a session file and update metadata."""
        sess_id = session_id or "default"
        fpath = self._session_file(sess_id)
        
        session_data: Dict[str, Any] = {
            "session_id": sess_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "title": content[:40].replace("\n", " ") if role == "user" else "New Chat",
            "messages": []
        }

        if fpath.exists():
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    session_data = json.load(f)
            except Exception:
                pass

        session_data["updated_at"] = datetime.utcnow().isoformat() + "Z"
        if not session_data.get("messages") and role == "user":
            session_data["title"] = content[:45].replace("\n", " ").strip()

        session_data.setdefault("messages", []).append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })

        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all chat sessions sorted by last updated timestamp descending."""
        self._ensure_storage()
        sessions = []
        for file in self.sessions_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    messages = data.get("messages", [])
                    first_user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
                    preview = first_user_msg[:75] if first_user_msg else (messages[0].get("content", "")[:75] if messages else "Empty chat")
                    title = data.get("title") or (first_user_msg[:35] if first_user_msg else file.stem)
                    sess_id = data.get("session_id", file.stem)
                    sessions.append({
                        "id": sess_id,
                        "session_id": sess_id,
                        "title": title,
                        "preview": preview,
                        "created_at": data.get("created_at", ""),
                        "updated_at": data.get("updated_at", ""),
                        "message_count": len(messages)
                    })
            except Exception:
                continue

        # Sort newest updated first
        sessions.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
        return sessions

    def delete_session(self, session_id: str) -> bool:
        """Delete a single chat session."""
        fpath = self._session_file(session_id)
        if fpath.exists():
            try:
                fpath.unlink()
                return True
            except Exception:
                return False
        return False

    def clear_all(self):
        """Wipe all session history files."""
        self._ensure_storage()
        for file in self.sessions_dir.glob("*.json"):
            try:
                file.unlink()
            except Exception:
                pass

    def get_all(self) -> List[Dict[str, str]]:
        """Backward compatibility helper for default session."""
        sessions = self.list_sessions()
        if sessions:
            return self.get_session_messages(sessions[0]["session_id"])
        return []

chat_history_db = ChatHistoryManager()
