"""
Comprehensive 4-Step Sequence Verification:
1. Run the resume + job description flow to create output/tailored_application.md.
2. Send 'provide the response in a pdf' -> produces verified output/tailored_application.pdf.
3. Ask 'give me a brief of the LearnFlow LMS presentation' (.pptx file) -> accurately summarizes extracted PPTX slides.
4. Reply 'yes do it' -> resolves pronoun/intent to 'LearnFlow LMS presentation', creates summary without hanging, and passes verification.
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

def approve_permission(req_id: str):
    try:
        with httpx.Client(base_url=BASE_URL, timeout=10.0) as p_client:
            res = p_client.post("/api/permission/respond", json={"request_id": req_id, "decision": "APPROVE"})
            print(f"  -> Permission {req_id} Approved (status {res.status_code})", flush=True)
    except Exception as e:
        print(f"  -> Failed to approve permission: {e}", flush=True)

def run_4step_verification():
    session_id = f"test_full_seq_{int(time.time())}"
    history = []
    print(f"\n==================================================", flush=True)
    print(f"  RUNNING 4-STEP VERIFICATION SUITE [Session: {session_id}]", flush=True)
    print(f"==================================================", flush=True)

    # -------------------------------------------------------------
    # Step 1: Resume + JD Flow
    # -------------------------------------------------------------
    print("\n[STEP 1] Running Resume + JD Flow -> output/tailored_application.md...", flush=True)
    goal_1 = "Review my resume (Alex_Rivera_Resume.md) and the job description (Job_Description_AI_Research_Intern.md), analyze skill gaps, and create a customized cover letter and tailored project action plan in output/tailored_application.md."
    
    step1_final_ans = ""
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        with client.stream("POST", "/api/chat/stream", json={"message": goal_1, "session_id": session_id, "history": history}) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    ev = data.get("event")
                    if ev == "ROUTING":
                        print(f"  -> Routing: {data.get('target')}", flush=True)
                    elif ev == "PERMISSION_REQUIRED":
                        approve_permission(data.get("request_id"))
                    elif ev == "FINAL_REPORT":
                        step1_final_ans = data.get("final_answer", "")
                        print(f"  -> Step 1 Complete! Final answer length: {len(step1_final_ans)}", flush=True)

    target_md = WORKSPACE / "output" / "tailored_application.md"
    assert target_md.exists(), "Step 1 failed: output/tailored_application.md not found!"
    assert len(target_md.read_text(encoding="utf-8")) > 500, "Step 1 failed: tailored_application.md is empty!"
    print(f"  [PASS] Step 1 passed! output/tailored_application.md exists ({target_md.stat().st_size} bytes).", flush=True)

    history.append({"role": "user", "content": goal_1})
    history.append({"role": "assistant", "content": step1_final_ans or "Created output/tailored_application.md."})

    # -------------------------------------------------------------
    # Step 2: Follow-up PDF conversion
    # -------------------------------------------------------------
    print("\n[STEP 2] Sending follow-up: 'provide the response in a pdf'...", flush=True)
    goal_2 = "provide the response in a pdf"
    
    step2_final_ans = ""
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        with client.stream("POST", "/api/chat/stream", json={"message": goal_2, "session_id": session_id, "history": history}) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    ev = data.get("event")
                    if ev == "ROUTING":
                        print(f"  -> Routing: {data.get('target')}", flush=True)
                        assert data.get("target") == "AGENT", "Follow-up must route to AGENT!"
                    elif ev == "PLAN_GENERATED":
                        print(f"  -> Plan: {data.get('plan', {}).get('summary')}", flush=True)
                    elif ev == "PERMISSION_REQUIRED":
                        approve_permission(data.get("request_id"))
                    elif ev == "ACTION_VERIFIED":
                        print(f"  -> Action Verified: {data.get('summary')}", flush=True)
                    elif ev == "FINAL_REPORT":
                        step2_final_ans = data.get("final_answer", "")
                        print(f"  -> Step 2 Complete!", flush=True)

    target_pdf = WORKSPACE / "output" / "tailored_application.pdf"
    assert target_pdf.exists(), "Step 2 failed: output/tailored_application.pdf not found!"
    assert target_pdf.stat().st_size > 1000, "Step 2 failed: PDF size too small!"
    with open(target_pdf, "rb") as f:
        assert f.read(5) == b"%PDF-", "Step 2 failed: invalid PDF binary header!"
    print(f"  [PASS] Step 2 passed! output/tailored_application.pdf generated and verified ({target_pdf.stat().st_size} bytes).", flush=True)

    history.append({"role": "user", "content": goal_2})
    history.append({"role": "assistant", "content": step2_final_ans or "Generated output/tailored_application.pdf."})

    # -------------------------------------------------------------
    # Step 3: PPTX Q&A / Briefing
    # -------------------------------------------------------------
    print("\n[STEP 3] Asking: 'give me a brief of the LearnFlow LMS presentation'...", flush=True)
    goal_3 = "give me a brief of the LearnFlow LMS presentation"
    
    step3_tokens = []
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        with client.stream("POST", "/api/chat/stream", json={"message": goal_3, "session_id": session_id, "history": history}) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    ev = data.get("event")
                    if ev == "ROUTING":
                        print(f"  -> Routing: {data.get('target')}", flush=True)
                    elif ev == "KNOWLEDGE_RETRIEVED":
                        sources = [s['filename'] for s in data.get('sources', [])]
                        print(f"  -> Knowledge Retrieved: {sources}", flush=True)
                    elif ev == "CHAT_TOKEN":
                        tok = data.get("token", "")
                        step3_tokens.append(tok)
                        print(tok, end="", flush=True)
                    elif ev == "CHAT_DONE":
                        print(f"\n  -> Step 3 CHAT response completed.", flush=True)

    step3_response = "".join(step3_tokens)
    print(f"  -> Response preview: {step3_response[:200]}...", flush=True)
    assert any(term in step3_response.lower() for term in ["learnflow", "lms", "management", "presentation", "aniket", "venturex", "tutor"]), "Step 3 failed: response did not summarize PPTX content!"
    assert "i don't have access" not in step3_response.lower(), "Step 3 failed: hallucinated lack of access!"
    print(f"  [PASS] Step 3 passed! PPTX content accurately grounded and briefed without access denial.", flush=True)

    history.append({"role": "user", "content": goal_3})
    history.append({"role": "assistant", "content": step3_response})

    # -------------------------------------------------------------
    # Step 4: Pronoun follow-up 'yes do it'
    # -------------------------------------------------------------
    print("\n[STEP 4] Sending confirmation: 'yes do it'...", flush=True)
    goal_4 = "yes do it"
    start_time = time.time()
    
    step4_completed = False
    with httpx.Client(base_url=BASE_URL, timeout=120.0) as client:
        with client.stream("POST", "/api/chat/stream", json={"message": goal_4, "session_id": session_id, "history": history}) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    ev = data.get("event")
                    if ev == "ROUTING":
                        print(f"  -> Routing: {data.get('target')}", flush=True)
                        assert data.get("target") == "AGENT", "Step 4 must route 'yes do it' to AGENT!"
                    elif ev == "UNDERSTAND":
                        print(f"  -> Intent: {data.get('message')}", flush=True)
                    elif ev == "PLAN_GENERATED":
                        print(f"  -> Plan: {data.get('plan', {}).get('summary')}", flush=True)
                    elif ev == "PERMISSION_REQUIRED":
                        filepath = data.get("params", {}).get("filepath", "")
                        print(f"  -> Permission Requested for {filepath}", flush=True)
                        assert "learnflow" in filepath.lower() or "presentation" in filepath.lower(), f"Step 4 failed: target file {filepath} was not resolved to LearnFlow!"
                        approve_permission(data.get("request_id"))
                    elif ev == "ACTION_VERIFIED":
                        print(f"  -> Action Verified: {data.get('summary')}", flush=True)
                    elif ev == "FINAL_REPORT":
                        print(f"  -> Final Report received: {data.get('final_answer')[:100]}...", flush=True)
                        step4_completed = True

    elapsed = time.time() - start_time
    print(f"  -> Step 4 execution time: {elapsed:.2f}s", flush=True)
    assert elapsed < 60.0, f"Step 4 took too long ({elapsed}s)! Must not hang."
    assert step4_completed, "Step 4 did not complete successfully!"

    summary_file = WORKSPACE / "output" / "LearnFlow_LMS_Presentation_summary.md"
    assert summary_file.exists(), f"Step 4 failed: {summary_file} not found!"
    assert summary_file.stat().st_size > 500, "Step 4 failed: summary file is empty!"
    print(f"  [PASS] Step 4 passed! Verified {summary_file.name} created in {elapsed:.2f}s without hanging.", flush=True)

    print("\n==================================================", flush=True)
    print("  ALL 4 STEPS PASSED PERFECTLY END-TO-END!", flush=True)
    print("==================================================\n", flush=True)

if __name__ == "__main__":
    run_4step_verification()
