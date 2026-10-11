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

async def run_deictic_guardrail_suite():
    session_id = f"test_deictic_guard_{int(time.time())}"
    print(f"\n==================================================", flush=True)
    print(f"  RUNNING DEICTIC SAVE GUARDRAIL SUITE [Session: {session_id}]", flush=True)
    print(f"==================================================", flush=True)

    # Prepare a test document in workspace
    test_doc_name = "test_guardrail_spec.txt"
    test_doc_path = WORKSPACE / test_doc_name
    test_doc_content = (
        "Project Vanguard Specification\n"
        "1. Core Objective: High-throughput event streaming architecture.\n"
        "2. Components: Kafka cluster, Rust stream processors, ClickHouse analytics.\n"
        "3. Metrics: Sub-5ms processing latency at 50,000 events/sec."
    )
    test_doc_path.write_text(test_doc_content, encoding="utf-8")

    # Set as last uploaded file in session
    agent_orchestrator.set_last_uploaded_file(session_id, test_doc_name)

    # -------------------------------------------------------------
    # Scenario A: "summarize this document" (deictic, NO save intent)
    # Expected: 1-step read_file plan, NO create_file, delivers chat text, NO file on disk
    # -------------------------------------------------------------
    goal_a = "summarize this document"
    print(f"\n[SCENARIO A] Asking: '{goal_a}' (Deictic, NO save intent)...", flush=True)

    plan_a = None
    final_answer_a = ""
    created_files_before = set(WORKSPACE.rglob("output/*"))

    async for ev in agent_orchestrator.run_pipeline(goal_a, session_id):
        ev_name = ev.get("event")
        if ev_name == "UNDERSTAND":
            print(f"  -> Understand: {ev.get('message')}", flush=True)
        elif ev_name == "PLAN_GENERATED":
            plan_a = ev.get("plan")
            print(f"  -> Plan steps: {[s.get('tool') for s in plan_a.get('steps', [])]}", flush=True)
        elif ev_name == "FINAL_REPORT":
            final_answer_a = ev.get("final_answer", "")
            print(f"  -> Final report received (len: {len(final_answer_a)})", flush=True)

    # Assertions for Scenario A
    assert plan_a is not None, "Plan was not generated for Scenario A"
    tools_a = [s.get("tool") for s in plan_a.get("steps", [])]
    assert "create_file" not in tools_a, f"Violation: create_file was present in plan for plain summary! Tools: {tools_a}"
    assert "create_folder" not in tools_a, f"Violation: create_folder was present in plan! Tools: {tools_a}"
    assert "read_file" in tools_a, f"Expected read_file step in plan! Tools: {tools_a}"
    assert len(final_answer_a) > 50, "Expected non-empty chat summary response"

    # Verify no unwanted output file was created
    created_files_after = set(WORKSPACE.rglob("output/*"))
    new_files_a = created_files_after - created_files_before
    assert len(new_files_a) == 0, f"Violation: Unwanted file(s) created on disk during plain summary: {new_files_a}"
    print(f"  [PASS] Scenario A passed: Clean chat response with zero file creation.", flush=True)

    # -------------------------------------------------------------
    # Scenario B: "summarize this document and save it as output/vanguard_summary.md" (explicit save intent)
    # Expected: 2-step plan (read_file + create_file), creates output/vanguard_summary.md on disk
    # -------------------------------------------------------------
    goal_b = "summarize this document and save it as output/vanguard_summary.md"
    print(f"\n[SCENARIO B] Asking: '{goal_b}' (Deictic WITH explicit save intent)...", flush=True)

    target_md_b = WORKSPACE / "output" / "vanguard_summary.md"
    if target_md_b.exists():
        target_md_b.unlink()

    plan_b = None
    step_b_completed = False

    async def auto_approver():
        while not step_b_completed:
            await asyncio.sleep(0.05)
            for req_id in list(permission_gateway._pending_requests.keys()):
                permission_gateway.resolve_request(PermissionResponse(request_id=req_id, decision="APPROVE"))
                print(f"  -> Auto-approved permission: {req_id}", flush=True)

    approver_task = asyncio.create_task(auto_approver())

    async for ev in agent_orchestrator.run_pipeline(goal_b, session_id):
        ev_name = ev.get("event")
        if ev_name == "PLAN_GENERATED":
            plan_b = ev.get("plan")
            print(f"  -> Plan steps: {[s.get('tool') for s in plan_b.get('steps', [])]}", flush=True)
        elif ev_name == "FINAL_REPORT":
            print(f"  -> Final report received.", flush=True)
            step_b_completed = True

    approver_task.cancel()

    # Assertions for Scenario B
    assert plan_b is not None, "Plan was not generated for Scenario B"
    tools_b = [s.get("tool") for s in plan_b.get("steps", [])]
    assert "create_file" in tools_b, f"Expected create_file in plan for explicit save request! Tools: {tools_b}"
    assert target_md_b.exists(), f"Failed: {target_md_b} was not created on disk!"
    assert len(target_md_b.read_text(encoding="utf-8")) > 50, "Saved file is empty or too short"
    print(f"  [PASS] Scenario B passed: File created correctly on disk when save requested.", flush=True)

    # -------------------------------------------------------------
    # Scenario C: "save the response you gave me in a file named output/chat_saved.md" (prior response save)
    # Expected: Saves the exact prior assistant response text from Scenario A
    # -------------------------------------------------------------
    goal_c = "save the response you gave me in a file named output/chat_saved.md"
    print(f"\n[SCENARIO C] Asking: '{goal_c}' (Prior response save)...", flush=True)

    history_c = [
        {"role": "user", "content": goal_a},
        {"role": "assistant", "content": final_answer_a}
    ]

    target_md_c = WORKSPACE / "output" / "chat_saved.md"
    if target_md_c.exists():
        target_md_c.unlink()

    step_c_completed = False

    async def auto_approver_c():
        while not step_c_completed:
            await asyncio.sleep(0.05)
            for req_id in list(permission_gateway._pending_requests.keys()):
                permission_gateway.resolve_request(PermissionResponse(request_id=req_id, decision="APPROVE"))
                print(f"  -> Auto-approved permission: {req_id}", flush=True)

    approver_task_c = asyncio.create_task(auto_approver_c())

    async for ev in agent_orchestrator.run_pipeline(goal_c, session_id, history=history_c):
        ev_name = ev.get("event")
        if ev_name == "FINAL_REPORT":
            print(f"  -> Final report received.", flush=True)
            step_c_completed = True

    approver_task_c.cancel()

    # Assertions for Scenario C
    assert target_md_c.exists(), f"Failed: {target_md_c} was not created!"
    saved_c_text = target_md_c.read_text(encoding="utf-8")
    assert saved_c_text.strip() == final_answer_a.strip(), "Saved content did not match prior assistant answer!"
    print(f"  [PASS] Scenario C passed: Exact prior response saved without hallucination.", flush=True)

    # Cleanup test files
    if test_doc_path.exists():
        test_doc_path.unlink()
    if target_md_b.exists():
        target_md_b.unlink()
    if target_md_c.exists():
        target_md_c.unlink()

    print(f"\n==================================================", flush=True)
    print("  ALL DEICTIC GUARDRAIL & SHORTCUT TESTS PASSED!", flush=True)
    print("==================================================\n", flush=True)

if __name__ == "__main__":
    asyncio.run(run_deictic_guardrail_suite())
