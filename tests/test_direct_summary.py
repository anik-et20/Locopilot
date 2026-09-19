import sys
import json
import time
from pathlib import Path
import httpx
import asyncio

sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent.parent
WORKSPACE = PROJECT_ROOT / "workspace"
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app

async def run_direct_summary_test():
    session_id = f"test_summary_{int(time.time())}"
    print(f"\n==================================================", flush=True)
    print(f"  RUNNING DIRECT SUMMARY TEST [Session: {session_id}]", flush=True)
    print(f"==================================================", flush=True)

    # 1. Create a dummy test file with real text
    test_text = (
        "Project Orion Phase 1 Specification\n"
        "Executive Summary: Project Orion aims to replace the legacy monolith with a microservices architecture. "
        "The primary goal is to reduce latency by 40% and increase deployment frequency. "
        "Key components include the User Service (Node.js), Product Service (Go), and Checkout Service (Python). "
        "Migration will occur in three stages over 6 months, starting with non-critical read paths. "
        "Budget allocated is $1.2M, with a team of 15 engineers. "
        "Risks include potential downtime during the database cutover and API backward compatibility. "
        "The new system will use PostgreSQL for relational data and Redis for caching.\n"
        * 10 # make it ~2KB
    )
    
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", timeout=120.0) as client:
        upload_res = await client.post(
            "/api/workspace/upload", 
            files=[("files", ("test_orion_spec.txt", test_text.encode('utf-8'), "text/plain"))], 
            data={"session_id": session_id}
        )
        assert upload_res.status_code == 200, "Failed to upload test file"
        
        goal = "give me a detailed summary of the test_orion_spec.txt file I just uploaded"
        
        print("\n[STEP 1] Asking for summary...", flush=True)
        
        step_completed = False
        final_answer = ""
        start_time = time.time()
        
        async with client.stream("POST", "/api/chat/stream", json={"message": goal, "session_id": session_id}) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    ev = data.get("event")
                    if ev == "ROUTING":
                        print(f"  -> Routing: {data.get('target')}", flush=True)
                    elif ev == "UNDERSTAND":
                        print(f"  -> Understand: {data.get('message')}", flush=True)
                    elif ev == "FINAL_REPORT":
                        final_answer = data.get("final_answer", "")
                        print(f"  -> Final Report received. Length: {len(final_answer)}", flush=True)
                        step_completed = True

    elapsed = time.time() - start_time
    print(f"  -> Execution time: {elapsed:.2f}s", flush=True)
    
    assert step_completed, "Did not receive FINAL_REPORT"
    assert "Could not generate a rich summary" not in final_answer, "Hit the generic fallback"
    assert len(final_answer) > 150, "Summary is too short"
    assert "Orion" in final_answer or "microservices" in final_answer, "Summary did not capture actual document content"
    
    assert "Full AI summary unavailable" not in final_answer, "Hit the extracted text fallback, synthesis still failed"

    # Cleanup test file
    test_file_path = WORKSPACE / "test_orion_spec.txt"
    if test_file_path.exists():
        test_file_path.unlink()

    print(f"  [PASS] Direct summary test passed successfully!\n", flush=True)

if __name__ == "__main__":
    asyncio.run(run_direct_summary_test())
