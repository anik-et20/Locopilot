"""
LocalGPT FastAPI Application Server
Provides REST endpoints and SSE streaming for the LocalGPT frontend dashboard.
"""
import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .core.config import settings
from .core.llm import ollama_client
from .core.rag import knowledge_base
from .core.tools import list_files, read_file
from .core.permission import permission_gateway, PermissionResponse
from .core.audit import audit_logger
from .core.agent_orchestrator import agent_orchestrator

# Setup Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("localgpt.api")

app = FastAPI(
    title="LocalGPT API",
    description="Privacy-first on-device AI Agent with deterministic sandboxing and human permission gates.",
    version=settings.version
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RunGoalRequest(BaseModel):
    goal: str
    session_id: Optional[str] = None

class PermissionDecisionRequest(BaseModel):
    request_id: str
    decision: str  # "APPROVE", "REJECT", "MODIFY"
    modified_params: Optional[Dict[str, Any]] = None
    user_comment: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing LocalGPT backend...")
    # Build initial RAG index
    index_res = knowledge_base.build_index()
    logger.info(f"Knowledge index initialized with {index_res.get('total_chunks', 0)} chunks.")

# --- API Endpoints ---

@app.get("/api/health")
async def health_check():
    """Health check for Ollama, LLM model, RAG index, and workspace."""
    ollama_status = ollama_client.check_health()
    files_res = list_files()
    return {
        "status": "online",
        "app_name": settings.app_name,
        "version": settings.version,
        "ollama": ollama_status,
        "rag": {
            "indexed_chunks": len(knowledge_base.chunks),
            "indexed_files": knowledge_base._indexed_files
        },
        "workspace": {
            "total_files": files_res.get("total_items", 0),
            "path": str(settings.workspace_dir)
        }
    }

@app.get("/api/workspace/files")
async def get_workspace_files(subpath: str = ""):
    """List all files in workspace directory."""
    try:
        return list_files(subpath)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/workspace/file")
async def get_workspace_file(filepath: str = Query(..., description="Relative path of file to view")):
    """Read full content of a file in workspace."""
    try:
        return read_file(filepath)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/workspace/reindex")
async def reindex_knowledge_base():
    """Rebuild RAG vector index over workspace."""
    res = knowledge_base.build_index()
    return res

@app.post("/api/agent/run")
async def run_agent_pipeline(req: RunGoalRequest):
    """Run the complete agent pipeline and stream events using Server-Sent Events (SSE)."""
    if not req.goal.strip():
        raise HTTPException(status_code=400, detail="Goal cannot be empty.")

    async def event_generator():
        try:
            async for event_data in agent_orchestrator.run_pipeline(req.goal, req.session_id):
                payload = json.dumps(event_data)
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.error(f"Error in pipeline stream: {e}", exc_info=True)
            err_payload = json.dumps({
                "event": "ERROR",
                "message": str(e)
            })
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/permission/pending")
async def get_pending_permissions():
    """Get list of active permission requests currently awaiting human review."""
    pending = permission_gateway.get_all_pending()
    return {"pending_requests": [p.model_dump() for p in pending]}

@app.post("/api/permission/respond")
async def respond_to_permission(req: PermissionDecisionRequest):
    """Submit human decision (Approve, Reject, or Modify) for a pending tool execution."""
    resp = PermissionResponse(
        request_id=req.request_id,
        decision=req.decision.upper(),
        modified_params=req.modified_params,
        user_comment=req.user_comment
    )
    success = permission_gateway.resolve_request(resp)
    if not success:
        raise HTTPException(status_code=404, detail=f"Permission request '{req.request_id}' not found or already resolved.")
    return {"status": "resolved", "decision": req.decision.upper()}

@app.get("/api/audit/logs")
async def get_audit_logs(session_id: Optional[str] = None, limit: int = 100):
    """Fetch timestamped audit log records."""
    entries = audit_logger.get_entries(session_id=session_id, limit=limit)
    return {
        "total_entries": len(entries),
        "entries": entries
    }

# Mount Frontend static files
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        return FileResponse(FRONTEND_DIR / "index.html")
