"""
Permission Gateway & Risk Analyzer
Enforces human-in-the-loop permission checks for all high-risk workspace actions.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
from .config import settings

logger = logging.getLogger("localgpt.permission")

class PermissionRequest(BaseModel):
    request_id: str
    session_id: str
    step_id: int
    tool_name: str
    risk_level: str
    params: Dict[str, Any]
    reasoning: str
    preview: Optional[str] = None

class PermissionResponse(BaseModel):
    request_id: str
    decision: str  # "APPROVE", "REJECT", "MODIFY"
    modified_params: Optional[Dict[str, Any]] = None
    user_comment: Optional[str] = None

class PermissionGateway:
    def __init__(self):
        # Maps request_id -> asyncio.Future
        self._pending_futures: Dict[str, asyncio.Future] = {}
        self._pending_requests: Dict[str, PermissionRequest] = {}

    def assess_risk(self, tool_name: str, params: Dict[str, Any]) -> str:
        """Evaluate whether a tool invocation requires human permission."""
        if tool_name in settings.high_risk_tools:
            return "HIGH"
        return "LOW"

    def create_request(
        self,
        request_id: str,
        session_id: str,
        step_id: int,
        tool_name: str,
        params: Dict[str, Any],
        reasoning: str
    ) -> PermissionRequest:
        """Create and register a permission request."""
        risk_level = self.assess_risk(tool_name, params)
        
        # Build human-friendly preview
        preview = None
        if tool_name == "create_file":
            filepath = params.get("filepath", "")
            content = params.get("content", "")
            preview = f"Target File: {filepath}\n\nContent Preview ({len(content)} chars):\n" + (content[:300] + "..." if len(content) > 300 else content)
        elif tool_name == "create_folder":
            preview = f"Target Directory: {params.get('folderpath', '')}"

        req = PermissionRequest(
            request_id=request_id,
            session_id=session_id,
            step_id=step_id,
            tool_name=tool_name,
            risk_level=risk_level,
            params=params,
            reasoning=reasoning,
            preview=preview
        )
        
        loop = asyncio.get_event_loop()
        self._pending_futures[request_id] = loop.create_future()
        self._pending_requests[request_id] = req
        return req

    async def wait_for_decision(self, request_id: str, timeout: float = 300.0) -> PermissionResponse:
        """Pause agent execution until human approval or rejection is received."""
        if request_id not in self._pending_futures:
            raise KeyError(f"No pending permission request found for ID {request_id}")

        future = self._pending_futures[request_id]
        try:
            decision = await asyncio.wait_for(future, timeout=timeout)
            return decision
        except asyncio.TimeoutError:
            logger.warning(f"Permission request {request_id} timed out after {timeout}s.")
            return PermissionResponse(
                request_id=request_id,
                decision="REJECT",
                user_comment="Automatic timeout rejection."
            )
        finally:
            self._pending_futures.pop(request_id, None)
            self._pending_requests.pop(request_id, None)

    def resolve_request(self, response: PermissionResponse) -> bool:
        """Deliver user's approval or rejection into the waiting execution future."""
        request_id = response.request_id
        if request_id in self._pending_futures and not self._pending_futures[request_id].done():
            self._pending_futures[request_id].set_result(response)
            logger.info(f"Resolved permission request {request_id} with decision: {response.decision}")
            return True
        return False

    def get_pending_request(self, request_id: str) -> Optional[PermissionRequest]:
        return self._pending_requests.get(request_id)

    def get_all_pending(self) -> list[PermissionRequest]:
        return list(self._pending_requests.values())

permission_gateway = PermissionGateway()
