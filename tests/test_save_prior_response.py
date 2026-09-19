import sys
import json
import time
from pathlib import Path
import asyncio

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE = PROJECT_ROOT / "workspace"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.agent_orchestrator import agent_orchestrator
from backend.core.permission import permission_gateway, PermissionResponse

async def run_save_prior_response_test():
    session_id = f"test_save_prior_{int(time.time())}"
    print(f"\n==================================================", flush=True)
    print(f"  RUNNING SAVE PRIOR RESPONSE TEST [Session: {session_id}]", flush=True)
    print(f"==================================================", flush=True)

    prior_assistant_answer = (
        "### Verified Project Summary\n"
        "1. **Architecture Migration:** Monolith to microservices completed across 3 phases.\n"
        "2. **Latency Gains:** 40% reduction in p99 response times verified.\n"
        "3. **Technology Stack:** Go, Node.js, and Python microservices with PostgreSQL and Redis."
    )

    history = [
        {"role": "user", "content": "give me a brief summary of the project architecture"},
        {"role": "assistant", "content": prior_assistant_answer}
    ]

    # -------------------------------------------------------------
    # Test 1: Markdown file save
    # -------------------------------------------------------------
    goal_1 = "save the response you gave me in a file named output/test_saved_summary.md"
    print(f"\n[TEST 1] Asking: '{goal_1}'...", flush=True)

    target_md = WORKSPACE / "output" / "test_saved_summary.md"
    if target_md.exists():
        target_md.unlink()

    step1_completed = False

    async def auto_approver():
        while not step1_completed:
            await asyncio.sleep(0.05)
            for req_id in list(permission_gateway._pending_requests.keys()):
                permission_gateway.resolve_request(PermissionResponse(request_id=req_id, decision="APPROVE"))
                print(f"  -> Auto-approved permission: {req_id}", flush=True)

    approver_task = asyncio.create_task(auto_approver())

    async for ev in agent_orchestrator.run_pipeline(goal_1, session_id, history=history):
        ev_name = ev.get("event")
        if ev_name == "UNDERSTAND":
            print(f"  -> Understand: {ev.get('message')}", flush=True)
        elif ev_name == "PLAN_GENERATED":
            print(f"  -> Plan: {ev.get('plan', {}).get('summary')}", flush=True)
        elif ev_name == "TOOL_EXECUTED":
            print(f"  -> Tool Executed: {ev.get('tool')} (success: {ev.get('success')})", flush=True)
        elif ev_name == "ACTION_VERIFIED":
            print(f"  -> Verified: {ev.get('summary')}", flush=True)
        elif ev_name == "FINAL_REPORT":
            print(f"  -> Final report received.", flush=True)
            step1_completed = True

    approver_task.cancel()

    assert target_md.exists(), f"Failed: {target_md} was not created!"
    saved_text = target_md.read_text(encoding="utf-8")
    print(f"  -> Saved file content preview:\n{saved_text}\n", flush=True)
    assert saved_text.strip() == prior_assistant_answer.strip(), "Failed: saved content did not match exact prior assistant response!"
    print(f"  [PASS] Test 1 passed: Markdown file matched exact prior response without hallucination.", flush=True)

    # -------------------------------------------------------------
    # Test 2: PDF file save
    # -------------------------------------------------------------
    goal_2 = "save that response as output/test_saved_summary.pdf"
    print(f"\n[TEST 2] Asking: '{goal_2}'...", flush=True)

    target_pdf = WORKSPACE / "output" / "test_saved_summary.pdf"
    if target_pdf.exists():
        target_pdf.unlink()

    step2_completed = False

    async def auto_approver_2():
        while not step2_completed:
            await asyncio.sleep(0.05)
            for req_id in list(permission_gateway._pending_requests.keys()):
                permission_gateway.resolve_request(PermissionResponse(request_id=req_id, decision="APPROVE"))
                print(f"  -> Auto-approved permission: {req_id}", flush=True)

    approver_task_2 = asyncio.create_task(auto_approver_2())

    async for ev in agent_orchestrator.run_pipeline(goal_2, session_id, history=history):
        ev_name = ev.get("event")
        if ev_name == "UNDERSTAND":
            print(f"  -> Understand: {ev.get('message')}", flush=True)
        elif ev_name == "TOOL_EXECUTED":
            print(f"  -> Tool Executed: {ev.get('tool')} (success: {ev.get('success')})", flush=True)
        elif ev_name == "FINAL_REPORT":
            print(f"  -> Final report received.", flush=True)
            step2_completed = True

    approver_task_2.cancel()

    assert target_pdf.exists(), f"Failed: {target_pdf} was not created!"
    assert target_pdf.stat().st_size > 500, "Failed: PDF size too small!"
    with open(target_pdf, "rb") as f:
        assert f.read(5) == b"%PDF-", "Failed: Invalid PDF header!"
    print(f"  [PASS] Test 2 passed: PDF file successfully compiled from prior response ({target_pdf.stat().st_size} bytes).", flush=True)

    # Cleanup test files
    if target_md.exists():
        target_md.unlink()
    if target_pdf.exists():
        target_pdf.unlink()

    print(f"\n==================================================", flush=True)
    print("  ALL SAVE PRIOR RESPONSE TESTS PASSED PERFECTLY!", flush=True)
    print("==================================================\n", flush=True)

if __name__ == "__main__":
    asyncio.run(run_save_prior_response_test())
