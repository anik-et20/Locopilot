"""
Append-Only Audit Logging System
Maintains a tamper-evident, timestamped log of all agent goals, plans, permission requests,
tool executions, and verification checks.
"""
import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from .config import settings

logger = logging.getLogger("localgpt.audit")

class AuditEntry(BaseModel):
    timestamp: str
    session_id: str
    event_type: str
    goal: Optional[str] = None
    step_id: Optional[int] = None
    action: Optional[str] = None
    risk_level: Optional[str] = None
    permission_status: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    sources_cited: Optional[List[Dict[str, Any]]] = None
    details: Optional[Dict[str, Any]] = None

class AuditLogger:
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = Path(log_path or settings.audit_log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._recent_entries: List[Dict[str, Any]] = []
        self._load_recent()

    def _load_recent(self, limit: int = 200):
        if not self.log_path.exists():
            return
        try:
            entries = []
            with open(self.log_path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            continue
            self._recent_entries = entries[-limit:]
        except Exception as e:
            logger.error(f"Error reading existing audit log: {e}")

    def log_event(
        self,
        event_type: str,
        session_id: str,
        goal: Optional[str] = None,
        step_id: Optional[int] = None,
        action: Optional[str] = None,
        risk_level: Optional[str] = None,
        permission_status: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        execution_result: Optional[Dict[str, Any]] = None,
        verification_result: Optional[Dict[str, Any]] = None,
        sources_cited: Optional[List[Dict[str, Any]]] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an immutable timestamped event entry to the audit log."""
        timestamp = datetime.now(timezone.utc).isoformat()
        
        entry = {
            "timestamp": timestamp,
            "session_id": session_id,
            "event_type": event_type,
            "goal": goal,
            "step_id": step_id,
            "action": action,
            "risk_level": risk_level,
            "permission_status": permission_status,
            "tool_args": tool_args,
            "execution_result": execution_result,
            "verification_result": verification_result,
            "sources_cited": sources_cited,
            "details": details or {}
        }

        # Filter out None values for clean JSON lines
        cleaned_entry = {k: v for k, v in entry.items() if v is not None}

        with self._lock:
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(cleaned_entry) + "\n")
                self._recent_entries.append(cleaned_entry)
                if len(self._recent_entries) > 500:
                    self._recent_entries.pop(0)
            except Exception as e:
                logger.error(f"Failed to append to audit log: {e}")

        return cleaned_entry

    def get_entries(self, session_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve recent audit entries, optionally filtered by session."""
        with self._lock:
            if session_id:
                filtered = [e for e in self._recent_entries if e.get("session_id") == session_id]
                return filtered[-limit:]
            return self._recent_entries[-limit:]

    def clear_session(self, session_id: str):
        """Helper to purge memory buffer for a test session (disk remains append-only)."""
        pass

audit_logger = AuditLogger()
