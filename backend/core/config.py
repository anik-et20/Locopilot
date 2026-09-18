"""
LocalGPT Configuration
Centralized configuration for LocalGPT backend services.
"""
import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = Path(os.environ.get("LOCALPILOT_WORKSPACE_DIR", BASE_DIR / "workspace")).resolve()
LOGS_DIR = Path(os.environ.get("LOCALPILOT_LOGS_DIR", BASE_DIR / "logs")).resolve()
AUDIT_LOG_PATH = LOGS_DIR / "audit_log.jsonl"

# Ensure directories exist
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    app_name: str = "LocalGPT"
    version: str = "1.0.0"
    workspace_dir: Path = WORKSPACE_DIR
    logs_dir: Path = LOGS_DIR
    audit_log_path: Path = AUDIT_LOG_PATH
    
    # Ollama LLM Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    llm_temperature: float = 0.2
    llm_timeout: float = 180.0
    
    # RAG / Embedding Configuration
    embedding_model_name: str = "all-MiniLM-L6-v2"
    chunk_size: int = 450
    chunk_overlap: int = 75
    top_k_retrieval: int = 4
    
    # Tool Safety & Risk Definitions
    allowed_tools: list[str] = [
        "list_files",
        "read_file",
        "search_documents",
        "create_file",
        "create_folder"
    ]
    high_risk_tools: list[str] = [
        "create_file",
        "create_folder"
    ]

settings = Settings()
