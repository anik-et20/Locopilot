"""
Deterministic Tool Layer
Implements the 5 strictly whitelisted Python tools.
Guarantees path sandboxing within the workspace and prevents any arbitrary code/shell execution.
"""
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from .config import settings
from .rag import knowledge_base


_GENERIC_MATCH_WORDS = {
    'report', 'file', 'document', 'presentation', 'summary',
    'data', 'system', 'analysis', 'diagram', 'notes', 'description'
}


def find_file_in_goal(goal: str) -> Optional[str]:
    """Return the workspace file whose specific name best matches the goal."""
    goal_lower = goal.lower()
    best_match: Optional[str] = None
    best_score = 0
    best_extension_match = False

    try:
        for p in settings.workspace_dir.rglob("*"):
            if not p.is_file() or any(part.startswith(".") for part in p.parts):
                continue
            rel = p.relative_to(settings.workspace_dir).as_posix()
            if rel.startswith("output/") or rel.startswith("test_output/"):
                continue

            true_stem = p.name.split(".")[0]
            stem_words = true_stem.lower().replace("_", " ").replace("-", " ").split()
            hits = [
                word for word in stem_words
                if len(word) > 3
                and word not in _GENERIC_MATCH_WORDS
                and word in goal_lower
            ]
            score = len(hits)
            extension_match = p.suffix.lower().lstrip(".") in goal_lower
            if score > best_score or (score == best_score and extension_match and not best_extension_match):
                best_score = score
                best_match = rel
                best_extension_match = extension_match
    except Exception:
        pass

    return best_match if best_score > 0 else None

class ToolDefinition(BaseModel):
    name: str
    description: str
    risk_level: str  # "LOW" or "HIGH"
    parameters: Dict[str, Any]

class ToolResult(BaseModel):
    success: bool
    tool_name: str
    risk_level: str
    output: Any
    error: Optional[str] = None
    execution_time_ms: float = 0.0

def _safe_resolve_path(rel_or_abs_path: str) -> Path:
    """Resolve a path safely, preventing directory traversal outside WORKSPACE_DIR."""
    workspace = settings.workspace_dir.resolve()
    
    # Clean leading slashes / backslashes
    clean_path = rel_or_abs_path.strip().lstrip("/\\")
    
    # If user passed "workspace/foo.txt", strip redundant leading "workspace/"
    if clean_path.startswith("workspace/") or clean_path.startswith("workspace\\"):
        clean_path = clean_path[10:].lstrip("/\\")

    resolved_path = (workspace / clean_path).resolve()

    # Sandboxing check
    try:
        resolved_path.relative_to(workspace)
    except ValueError:
        raise PermissionError(f"Security Alert: Attempted path traversal outside workspace sandbox: '{rel_or_abs_path}'")

    return resolved_path

# --- The 5 Deterministic Tools ---

def list_files(subpath: str = "") -> Dict[str, Any]:
    """List files and subfolders inside the workspace directory."""
    target_dir = _safe_resolve_path(subpath)
    if not target_dir.exists():
        raise FileNotFoundError(f"Directory not found: {subpath}")
    if not target_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {subpath}")

    items = []
    for entry in target_dir.iterdir():
        rel = entry.relative_to(settings.workspace_dir).as_posix()
        stat = entry.stat()
        items.append({
            "name": entry.name,
            "relative_path": rel,
            "type": "directory" if entry.is_dir() else "file",
            "size_bytes": stat.st_size if entry.is_file() else None,
            "extension": entry.suffix if entry.is_file() else None
        })

    return {
        "directory": target_dir.relative_to(settings.workspace_dir).as_posix() or ".",
        "total_items": len(items),
        "items": items
    }

def read_file(filepath: str) -> Dict[str, Any]:
    """Read the full content of a file within the workspace."""
    target_file = _safe_resolve_path(filepath)
    if not target_file.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    if not target_file.is_file():
        raise IsADirectoryError(f"Path is a directory, not a file: {filepath}")

    ext = target_file.suffix.lower()
    if ext in [".pdf", ".pptx", ".docx"]:
        content = knowledge_base.load_document(target_file)
    else:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

    rel_path = target_file.relative_to(settings.workspace_dir).as_posix()
    return {
        "filepath": rel_path,
        "filename": target_file.name,
        "size_bytes": target_file.stat().st_size,
        "content": content
    }

def search_documents(query: str, top_k: int = 4) -> Dict[str, Any]:
    """Search local workspace documents using the RAG semantic knowledge engine."""
    results = knowledge_base.search(query=query, top_k=top_k)
    formatted = knowledge_base.format_retrieved_context(results)
    # Build per-result detail list for richer LLM context
    result_details = []
    for r in results:
        result_details.append({
            "filename": r.chunk.filename,
            "relative_path": r.chunk.relative_path,
            "score": r.score,
            "snippet": r.chunk.content[:400].strip()
        })
    return {
        "query": query,
        "num_results": len(results),
        "sources": formatted["sources"],
        "results": result_details,
        "context_block": formatted["formatted_block"],
        "indexed_files": knowledge_base._indexed_files,
        "total_indexed": len(knowledge_base._indexed_files)
    }

def create_file(filepath: str, content: str) -> Dict[str, Any]:
    """Create a new file or write content to a file in the workspace (High Risk)."""
    target_file = _safe_resolve_path(filepath)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    is_pdf = target_file.suffix.lower() == ".pdf"
    if is_pdf:
        try:
            from .pdf_generator import generate_pdf_from_markdown
            generate_pdf_from_markdown(content, target_file)
        except ImportError:
            raise RuntimeError("PDF generation failed: 'reportlab' is not installed. Please run `pip install reportlab`.")
        except Exception as e:
            raise RuntimeError(f"PDF generation failed: {e}")
    else:
        with open(target_file, "w", encoding="utf-8") as f:
            f.write(content)

    # Re-index knowledge base so newly created file is searchable
    knowledge_base.build_index()

    rel_path = target_file.relative_to(settings.workspace_dir).as_posix()
    return {
        "filepath": rel_path,
        "filename": target_file.name,
        "size_bytes": target_file.stat().st_size,
        "bytes_written": target_file.stat().st_size,
        "format": "PDF" if is_pdf else "TEXT",
        "message": f"Successfully created {'binary PDF' if is_pdf else 'file'}: {rel_path}"
    }

def create_folder(folderpath: str) -> Dict[str, Any]:
    """Create a new folder in the workspace (High Risk)."""
    target_dir = _safe_resolve_path(folderpath)
    target_dir.mkdir(parents=True, exist_ok=True)

    rel_path = target_dir.relative_to(settings.workspace_dir).as_posix()
    return {
        "folderpath": rel_path,
        "foldername": target_dir.name,
        "message": f"Successfully created directory: {rel_path}"
    }

TOOL_REGISTRY = {
    "list_files": {
        "func": list_files,
        "risk": "LOW",
        "description": "List files and directories within the workspace.",
        "params_schema": {"subpath": "optional relative directory path, e.g. '' or 'output'"}
    },
    "read_file": {
        "func": read_file,
        "risk": "LOW",
        "description": "Read the text content of a specified file in the workspace.",
        "params_schema": {"filepath": "relative path to the file, e.g. 'Alex_Rivera_Resume.md'"}
    },
    "search_documents": {
        "func": search_documents,
        "risk": "LOW",
        "description": "Search local personal documents via semantic RAG.",
        "params_schema": {"query": "search query string", "top_k": "optional integer, default 4"}
    },
    "create_file": {
        "func": create_file,
        "risk": "HIGH",
        "description": "Create or overwrite a file with specific content in the workspace (Requires Permission).",
        "params_schema": {"filepath": "target relative filepath", "content": "text/markdown content to write"}
    },
    "create_folder": {
        "func": create_folder,
        "risk": "HIGH",
        "description": "Create a new folder in the workspace (Requires Permission).",
        "params_schema": {"folderpath": "target relative folderpath"}
    }
}

def execute_tool(tool_name: str, params: Dict[str, Any]) -> ToolResult:
    """Safely execute one of the 5 whitelisted tools with timing and error isolation."""
    if tool_name not in TOOL_REGISTRY:
        return ToolResult(
            success=False,
            tool_name=tool_name,
            risk_level="UNKNOWN",
            output=None,
            error=f"Unrecognized tool '{tool_name}'. Allowed tools: {list(TOOL_REGISTRY.keys())}",
            execution_time_ms=0.0
        )

    tool_info = TOOL_REGISTRY[tool_name]
    risk_level = tool_info["risk"]
    start_time = time.perf_counter()

    try:
        func = tool_info["func"]
        result = func(**params)
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ToolResult(
            success=True,
            tool_name=tool_name,
            risk_level=risk_level,
            output=result,
            execution_time_ms=round(duration_ms, 2)
        )
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ToolResult(
            success=False,
            tool_name=tool_name,
            risk_level=risk_level,
            output=None,
            error=str(e),
            execution_time_ms=round(duration_ms, 2)
        )
