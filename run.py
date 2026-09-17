"""
LocalGPT Runner Script
Launches the FastAPI backend and serves the interactive frontend dashboard.
"""
import sys
from backend.core.config import settings
import uvicorn

def main():
    print("=" * 65)
    print("  [*] Starting LocalGPT - Privacy-First AI Workspace Prototype")
    print(f"  [*] Mode: 100% On-Device Local Processing")
    print(f"  [*] LLM Engine: Ollama ({settings.ollama_model})")
    print(f"  [*] Workspace: {settings.workspace_dir}")
    print(f"  [*] Audit Trail: {settings.audit_log_path}")
    print("=" * 65)
    print("  [+] Web Dashboard available at: http://127.0.0.1:8000")
    print("=" * 65)

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False, log_level="info")

if __name__ == "__main__":
    main()
