"""
LocalPilot Runner Script
Launches the FastAPI backend and serves the interactive frontend dashboard.
"""
import sys
from setup_check import check_environment
from backend.core.config import settings
from pdf_generator import generate_report
import uvicorn

def main():
    # Run pre-flight checks
    is_ready = check_environment(auto_exit=False)
    if not is_ready:
        sys.exit(1)

    try:
        report_path = generate_report()
        print(f"  [+] Technical report PDF generated: {report_path}")
    except Exception as exc:
        print(f"  [!] PDF generation failed: {exc}")
        sys.exit(1)

    print("=" * 65)
    print("  [*] Starting LocalPilot - Privacy-First AI Workspace Prototype")
    print(f"  [*] Mode: 100% On-Device Local Processing")
    print(f"  [*] LLM Engine: Ollama ({settings.ollama_model})")
    print(f"  [*] Workspace: {settings.workspace_dir}")
    print(f"  [*] Audit Trail: {settings.audit_log_path}")
    print("=" * 65)
    print("  [+] Web Dashboard available at: http://127.0.0.1:8000")
    print("=" * 65)

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True, log_level="info")

if __name__ == "__main__":
    main()
