"""
Session-Aware Chat History Database
Persists chat conversations grouped by unique session IDs under settings.logs_dir / "chat_history.json".
Also maintains dual-sync with individual session files under settings.logs_dir / "chat_sessions".
"""
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import settings

class ChatHistoryManager:
    def __init__(self):
        self.history_file = settings.logs_dir / "chat_history.json"
        self.sessions_dir = settings.logs_dir / "chat_sessions"
        self._lock = threading.Lock()
        self._ensure_storage()

    def _ensure_storage(self):
        settings.logs_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._write_store({"sessions": {}})
        else:
            self._migrate_if_needed()

    def _read_store(self) -> Dict[str, Any]:
        """Read all sessions from chat_history.json."""
        if not self.history_file.exists():
            return {"sessions": {}}
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    if "sessions" in data:
                        return data
                    return {"sessions": data}
                elif isinstance(data, list):
                    # Migrate legacy flat list to default session
                    return {
                        "sessions": {
                            "default": {
                                "session_id": "default",
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "updated_at": datetime.now(timezone.utc).isoformat(),
                                "title": "Default Session",
                                "messages": data
                            }
                        }
                    }
        except Exception:
            pass
        return {"sessions": {}}

    def _write_store(self, data: Dict[str, Any]):
        """Write all sessions to chat_history.json."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _migrate_if_needed(self):
        """If individual session files exist in sessions_dir but not in chat_history.json, sync them."""
        store = self._read_store()
        sessions = store.get("sessions", {})
        updated = False
        for f in self.sessions_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as sf:
                    sdata = json.load(sf)
                    sid = sdata.get("session_id", f.stem)
                    if sid not in sessions:
                        sessions[sid] = sdata
                        updated = True
            except Exception:
                continue
        if updated:
            self._write_store({"sessions": sessions})

    def get_session_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve all messages for a session."""
        with self._lock:
            store = self._read_store()
            sessions = store.get("sessions", {})
            if session_id in sessions:
                return sessions[session_id].get("messages", [])
            
            # Fallback to sessions_dir
            safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_") or "default"
            fpath = self.sessions_dir / f"{safe_id}.json"
            if fpath.exists():
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get("messages", [])
                except Exception:
                    pass
            return []

    def add_message(self, session_id: Optional[str], role: str, content: str):
        """Append a message to a session and persist."""
        sess_id = session_id or "default"
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._lock:
            store = self._read_store()
            sessions = store.setdefault("sessions", {})
            if sess_id not in sessions:
                sessions[sess_id] = {
                    "session_id": sess_id,
                    "created_at": now_iso,
                    "updated_at": now_iso,
                    "title": content[:40].replace("\n", " ").strip() if role == "user" else "New Chat",
                    "messages": []
                }

            sdata = sessions[sess_id]
            sdata["updated_at"] = now_iso
            if not sdata.get("messages") and role == "user":
                sdata["title"] = content[:45].replace("\n", " ").strip()

            sdata.setdefault("messages", []).append({
                "role": role,
                "content": content,
                "timestamp": now_iso
            })

            self._write_store(store)

            # Also update individual session file in sessions_dir
            try:
                safe_id = "".join(c for c in sess_id if c.isalnum() or c in "-_") or "default"
                with open(self.sessions_dir / f"{safe_id}.json", "w", encoding="utf-8") as f:
                    json.dump(sdata, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Return list of sessions with metadata sorted by updated_at descending."""
        with self._lock:
            store = self._read_store()
            sessions = store.get("sessions", {})
            result = []
            for sess_id, sdata in sessions.items():
                messages = sdata.get("messages", [])
                first_user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
                preview = first_user_msg[:75] if first_user_msg else (messages[0].get("content", "")[:75] if messages else "Empty chat")
                title = sdata.get("title") or (first_user_msg[:35] if first_user_msg else sess_id)
                result.append({
                    "id": sess_id,
                    "session_id": sess_id,
                    "created_at": sdata.get("created_at", ""),
                    "updated_at": sdata.get("updated_at", ""),
                    "message_count": len(messages),
                    "title": title,
                    "preview": preview
                })
            result.sort(key=lambda s: s.get("updated_at", ""), reverse=True)
            return result

    def delete_session(self, session_id: str) -> bool:
        """Remove all messages for a session."""
        with self._lock:
            store = self._read_store()
            sessions = store.get("sessions", {})
            found = False
            if session_id in sessions:
                del sessions[session_id]
                found = True
                self._write_store(store)

            safe_id = "".join(c for c in session_id if c.isalnum() or c in "-_") or "default"
            fpath = self.sessions_dir / f"{safe_id}.json"
            if fpath.exists():
                try:
                    fpath.unlink()
                    found = True
                except Exception:
                    pass
            return found

    def clear_all(self):
        """Delete all chat history."""
        with self._lock:
            self._write_store({"sessions": {}})
            for f in self.sessions_dir.glob("*.json"):
                try:
                    f.unlink()
                except Exception:
                    pass

    def get_all(self) -> List[Dict[str, str]]:
        """Retrieve all messages across all sessions."""
        with self._lock:
            store = self._read_store()
            sessions = store.get("sessions", {})
            all_messages = []
            for sess_id, sdata in sessions.items():
                all_messages.extend(sdata.get("messages", []))
            return all_messages

chat_history_db = ChatHistoryManager()
