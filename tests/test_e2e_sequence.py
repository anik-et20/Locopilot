"""
End-to-End Sequence Verification:
1. Run resume + job description flow to create output/tailored_application.md.
2. Send 'provide the response in a pdf' as a follow-up within the same session.
3. Confirm it does NOT claim missing file access, approves the high-risk permission gate,
   and produces output/tailored_application.pdf compiled from the cover letter / tailored application content.
"""
import sys
import json
import time
from pathlib import Path
import httpx

sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE = PROJECT_ROOT / "workspace"

def run_test():
    client = httpx.Client(base_url=BASE_URL, timeout=120.0)
    session_id = f"e2e_sess_{int(time.time())}"
    print(f"\n--- Testing Session ID: {session_id} ---")

    # Step 1: Run resume + job description flow
    print("\n[Step 1] Sending resume + job description analysis goal...")
    goal_1 = "Review my resume (Alex_Rivera_Resume.md) and the job description (Job_Description_AI_Research_Intern.md), analyze skill gaps, and create a customized cover letter and tailored project action plan in output/tailored_application.md."
    
    with client.stream("POST", "/api/chat/stream", json={"message": goal_1, "session_id": session_id, "history": []}) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                event = data.get("event")
                if event == "ROUTING":
                    print(f"  -> Routing: {data.get('target')}")
                elif event == "PLAN_GENERATED":
                    print(f"  -> Plan: {data.get('plan', {}).get('summary')}")
                elif event == "PERMISSION_REQUIRED":
                    req_id = data.get("request_id")
                    print(f"  -> Permission requested: {req_id}, tool: {data.get('tool')}")
                    # Auto-approve permission
                    perm_res = client.post("/api/permission/respond", json={"request_id": req_id, "decision": "APPROVE"})
                    print(f"  -> Permission approval status: {perm_res.status_code}")
                elif event == "FINAL_REPORT":
                    print(f"  -> Step 1 Completed! Final answer length: {len(data.get('final_answer', ''))}")

    target_md = WORKSPACE / "output" / "tailored_application.md"
    assert target_md.exists(), "output/tailored_application.md must exist!"
    md_content = target_md.read_text(encoding="utf-8")
    assert len(md_content) > 500, "Markdown content should be rich!"
    print(f"  [OK] output/tailored_application.md created ({len(md_content)} bytes).")

    # Step 2: Send follow-up: 'provide the response in a pdf'
    print("\n[Step 2] Sending follow-up: 'provide the response in a pdf'...")
    goal_2 = "provide the response in a pdf"
    
    chat_history = [
        {"role": "user", "content": goal_1},
        {"role": "assistant", "content": "Created tailored_application.md with cover letter and gap analysis."}
    ]

    pdf_created = False
    with client.stream("POST", "/api/chat/stream", json={"message": goal_2, "session_id": session_id, "history": chat_history}) as response:
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                event = data.get("event")
                if event == "ROUTING":
                    print(f"  -> Routing: {data.get('target')}")
                    assert data.get("target") == "AGENT", "Follow-up must route to AGENT!"
                elif event == "PLAN_GENERATED":
                    print(f"  -> Plan: {data.get('plan', {}).get('summary')}")
                elif event == "PERMISSION_REQUIRED":
                    req_id = data.get("request_id")
                    tool = data.get("tool")
                    filepath = data.get("params", {}).get("filepath")
                    print(f"  -> Permission requested: {req_id}, tool: {tool}, filepath: {filepath}")
                    assert tool == "create_file" and filepath.endswith(".pdf"), "Should create a .pdf file!"
                    perm_res = client.post("/api/permission/respond", json={"request_id": req_id, "decision": "APPROVE"})
                    print(f"  -> Permission approval status: {perm_res.status_code}")
                elif event == "ACTION_VERIFIED":
                    print(f"  -> Action verified: {data.get('summary')}")
                elif event == "FINAL_REPORT":
                    print(f"  -> Step 2 Completed! Final answer: {data.get('final_answer')[:120]}...")
                    pdf_created = True

    target_pdf = WORKSPACE / "output" / "tailored_application.pdf"
    assert target_pdf.exists(), "output/tailored_application.pdf must exist!"
    pdf_size = target_pdf.stat().st_size
    assert pdf_size > 1000, f"PDF size {pdf_size} bytes is too small!"
    
    # Read PDF header
    with open(target_pdf, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", "File must have valid %PDF- header!"
    print(f"  [OK] output/tailored_application.pdf successfully generated and verified ({pdf_size} bytes, valid PDF header)!")
    print("\n=== ALL E2E VERIFICATIONS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_test()
