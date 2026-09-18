"""
LocalPilot Environment & Setup Verifier
Validates dependencies, Ollama connectivity, and target model availability before launch.
Prints clean, actionable error messages without raw stack traces.
"""
import sys
import importlib
from pathlib import Path
import httpx

REQUIRED_MODULES = [
    ("fastapi", "FastAPI framework", "pip install fastapi"),
    ("uvicorn", "Uvicorn ASGI server", "pip install uvicorn"),
    ("pydantic", "Pydantic validation", "pip install pydantic"),
    ("httpx", "HTTPX async client", "pip install httpx"),
    ("sklearn", "Scikit-learn TF-IDF engine", "pip install scikit-learn"),
    ("reportlab", "ReportLab PDF generation engine", "pip install reportlab"),
    ("pypdf", "PyPDF document reader", "pip install pypdf"),
    ("pptx", "python-pptx presentation reader", "pip install python-pptx"),
    ("docx", "python-docx document reader", "pip install python-docx"),
    ("multipart", "python-multipart form parser", "pip install python-multipart")
]

def check_environment(auto_exit: bool = False) -> bool:
    """Run all prerequisite checks and print formatted diagnosis."""
    from backend.core.config import settings
    
    issues = []
    
    print("=" * 65)
    print("  [*] Performing LocalPilot Pre-Flight Health Check...")
    print("=" * 65)

    # 1. Check Python Version (3.10+)
    if sys.version_info < (3, 10):
        print(f"\n  [!] Unsupported Python version: {sys.version.split()[0]}. Python 3.10+ is required.")
        issues.append("Python version is below 3.10.")
    else:
        print(f"  [OK] Python version: {sys.version.split()[0]} (>= 3.10).")
    
    # 2. Check Python Dependencies
    missing_deps = []
    for mod_name, desc, install_cmd in REQUIRED_MODULES:
        try:
            importlib.import_module(mod_name)
        except ImportError:
            missing_deps.append((mod_name, desc, install_cmd))
            
    if missing_deps:
        print("\n  [!] Missing Python Dependencies:")
        for mod_name, desc, install_cmd in missing_deps:
            print(f"      - {mod_name} ({desc}) -> Run: `{install_cmd}`")
        print("\n  [Tip] Run: `pip install -r requirements.txt` to install all requirements.")
        issues.append("Missing required Python packages.")
    else:
        print("  [OK] All required Python packages are installed.")

    # 2. Check Ollama Service
    ollama_online = False
    available_models = []
    try:
        with httpx.Client(timeout=4.0) as client:
            res = client.get(f"{settings.ollama_base_url}/api/tags")
            if res.status_code == 200:
                ollama_online = True
                data = res.json()
                available_models = [m.get("name", "") for m in data.get("models", [])]
                print(f"  [OK] Ollama service detected and reachable at {settings.ollama_base_url}.")
            else:
                issues.append(f"Ollama returned HTTP status {res.status_code}.")
    except Exception:
        print(f"\n  [!] Cannot connect to Ollama at {settings.ollama_base_url}.")
        print("      - Make sure Ollama is installed and running on your system.")
        print("      - Launch Ollama desktop app or run `ollama serve` in a terminal.")
        issues.append("Ollama service is unreachable.")

    # 3. Check Target Model
    if ollama_online:
        target = settings.ollama_model
        # Check if exact match or tag match exists
        model_found = any(target in m for m in available_models)
        if model_found:
            print(f"  [OK] Target model '{target}' is installed and ready.")
        else:
            print(f"\n  [!] Target model '{target}' is not yet pulled in Ollama.")
            print(f"      - Run: `ollama pull {target}` in your terminal.")
            if available_models:
                print(f"      - Currently installed models: {', '.join(available_models)}")
                print(f"      - Or update `ollama_model` in backend/core/config.py to one of your installed models.")
            issues.append(f"Target model '{target}' not found in Ollama.")

    # 4. Check Workspace Directory
    if settings.workspace_dir.exists():
        file_count = len(list(settings.workspace_dir.glob("*")))
        print(f"  [OK] Workspace directory active: {settings.workspace_dir} ({file_count} items).")
    else:
        print(f"  [+] Creating workspace directory at {settings.workspace_dir}...")
        settings.workspace_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 65)

    if issues:
        print(f"\n  [!] Setup Check: {len(issues)} issue(s) detected.")
        for idx, issue in enumerate(issues, 1):
            print(f"      {idx}. {issue}")
        print("\n  Please resolve the item(s) above before starting LocalPilot.\n")
        if auto_exit:
            sys.exit(1)
        return False
    else:
        print("  [OK] All pre-flight checks passed! Launching LocalPilot server...\n")
        return True

if __name__ == "__main__":
    check_environment(auto_exit=True)
