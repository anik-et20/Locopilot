"""
End-to-End Verification Tests for 5 LocalPilot Issues
"""
import os
import sys
import unittest
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import httpx
from backend.core.config import settings
from backend.core.pdf_generator import generate_pdf_from_markdown
from backend.core.verifier import action_verifier
from backend.core.chat_history import chat_history_db
from backend.core.audit import audit_logger
from setup_check import check_environment

def is_server_online():
    try:
        with httpx.Client(timeout=1.0) as check_client:
            return check_client.get("http://127.0.0.1:8000/api/health").status_code == 200
    except Exception:
        return False

def get_test_client():
    """Returns a fresh HTTP client targeting live server on 8000 if active, or in-process ASGITransport."""
    if is_server_online():
        return httpx.Client(base_url="http://127.0.0.1:8000", timeout=5.0)
    from backend.app import app
    return httpx.Client(transport=httpx.ASGITransport(app=app), base_url="http://test")


class TestLocalPilotFixes(unittest.TestCase):

    def test_issue_1_requirements_and_setup_check(self):
        """Verify requirements.txt and setup_check pre-flight."""
        req_file = PROJECT_ROOT / "requirements.txt"
        content = req_file.read_text(encoding="utf-8")
        self.assertIn("scikit-learn", content)
        self.assertIn("reportlab", content)
        self.assertNotIn("sentence-transformers", content)

        # Run pre-flight check function
        ready = check_environment(auto_exit=False)
        self.assertTrue(ready, "Pre-flight environment check should pass")

    def test_issue_2_pdf_generation_and_verification(self):
        """Verify PDF generation generates valid binary PDF and passes verifier."""
        test_pdf = PROJECT_ROOT / "workspace" / "test_output" / "unit_test_doc.pdf"
        test_pdf.parent.mkdir(parents=True, exist_ok=True)
        
        md_content = """# Unit Test Document
## Section A
This is a test paragraph with **bold** and *italic* text.

### Features
- Item 1
- Item 2

| Col A | Col B |
| --- | --- |
| 100 | 200 |
"""
        generate_pdf_from_markdown(md_content, test_pdf)
        self.assertTrue(test_pdf.exists(), "PDF should be generated")
        self.assertGreater(test_pdf.stat().st_size, 500, "PDF should have real content")

        # Verify action
        res = action_verifier.verify_action(
            tool_name="create_file",
            params={"filepath": "test_output/unit_test_doc.pdf", "content": md_content},
            execution_output={"filepath": "test_output/unit_test_doc.pdf", "bytes_written": test_pdf.stat().st_size}
        )
        self.assertTrue(res.verified, f"PDF verification failed: {res.summary_message}")
        
        # Cleanup
        if test_pdf.exists():
            test_pdf.unlink()

    def test_issue_3_audit_log_and_export_csv(self):
        """Verify audit log JSONL formatting and CSV export endpoint."""
        # Log a test event
        audit_logger.log_event(
            session_id="test_sess",
            event_type="UNIT_TEST_EVENT",
            details={"test_key": "test_val"},
            risk_level="LOW"
        )
        
        # Check backend endpoint
        with get_test_client() as client:
            res = client.get("/api/audit/export?format=csv")
            self.assertEqual(res.status_code, 200)
            self.assertIn("text/csv", res.headers.get("content-type", ""))
            csv_text = res.text
            self.assertIn("Timestamp", csv_text)
            self.assertIn("Event Type", csv_text)
            self.assertIn("UNIT_TEST_EVENT", csv_text)

    def test_issue_4_and_5_sessions_and_stream(self):
        """Verify multi-session chat history and endpoints."""
        session_id = f"test_session_{int(os.getpid())}"
        chat_history_db.add_message(session_id, "user", "Hello unit test")
        chat_history_db.add_message(session_id, "assistant", "Hello! How can I assist you?")

        sessions = chat_history_db.list_sessions()
        found = any(s["session_id"] == session_id for s in sessions)
        self.assertTrue(found, f"Session {session_id} should be in list_sessions")

        messages = chat_history_db.get_session_messages(session_id)
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["content"], "Hello unit test")

        # Test API endpoints
        with get_test_client() as client:
            res = client.get("/api/chat/sessions")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(any(s["id"] == session_id for s in data.get("sessions", [])))

            # Test session details endpoint
            res_sess = client.get(f"/api/chat/sessions/{session_id}")
            self.assertEqual(res_sess.status_code, 200)
            self.assertEqual(len(res_sess.json().get("messages", [])), 2)

            # Test delete session endpoint
            res_del = client.delete(f"/api/chat/sessions/{session_id}")
            self.assertEqual(res_del.status_code, 200)

        # Confirm deleted
        messages_after = chat_history_db.get_session_messages(session_id)
        self.assertEqual(len(messages_after), 0)

    def test_intent_classification_routing(self):
        """Verify broadened agent routing matches natural PDF and retry phrasing."""
        import asyncio
        from backend.core.chat import chat_manager

        test_cases = [
            ("provide the response in a pdf", "AGENT"),
            ("give in pdf format", "AGENT"),
            ("make it a pdf", "AGENT"),
            ("convert to pdf", "AGENT"),
            ("export as pdf", "AGENT"),
            ("now try again doing the same thing", "AGENT"),
            ("try again", "AGENT"),
            ("convert that to pdf", "AGENT"),
            ("Review my resume and create tailored_application.md", "AGENT"),
            ("hi", "CHAT"),
            ("hello", "CHAT"),
        ]

        for text, expected in test_cases:
            route = asyncio.run(chat_manager._classify_intent(text))
            self.assertEqual(route, expected, f"Query '{text}' should route to {expected}, got {route}")

    def test_orchestrator_last_output_and_followup_detection(self):
        """Verify orchestrator tracks last_output_file and detects follow-up conversion requests."""
        from backend.core.agent_orchestrator import agent_orchestrator

        sess_id = "test_orchestrator_sess"
        agent_orchestrator.set_last_output_file(sess_id, "output/tailored_application.md")
        self.assertEqual(agent_orchestrator.get_last_output_file(sess_id), "output/tailored_application.md")

        self.assertTrue(agent_orchestrator._is_followup_conversion_request("provide the response in a pdf"))
        self.assertTrue(agent_orchestrator._is_followup_conversion_request("give in pdf format"))
        self.assertTrue(agent_orchestrator._is_followup_conversion_request("convert that to pdf"))
        self.assertTrue(agent_orchestrator._is_followup_conversion_request("now try again doing the same thing"))
        self.assertFalse(agent_orchestrator._is_followup_conversion_request("What skills does Alex have?"))

    def test_rag_search_on_uploaded_files(self):
        """Verify: place a text file in workspace → build_index → search returns results."""
        from backend.core.rag import KnowledgeBase

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Create a realistic document with searchable content
            doc = tmp_path / "john_doe_resume.txt"
            doc.write_text(
                "John Doe - Software Engineer\n\n"
                "Skills: Python, FastAPI, Machine Learning, TensorFlow, PostgreSQL\n\n"
                "Experience:\n"
                "  - Senior Engineer at Acme Corp (2020-2024): Built scalable REST APIs\n"
                "  - ML Engineer at DataCo (2018-2020): Trained neural network models\n\n"
                "Education: B.S. Computer Science, MIT, 2018\n\n"
                "Projects: Built a recommendation system using collaborative filtering.",
                encoding="utf-8"
            )

            kb = KnowledgeBase(workspace_dir=tmp_path)
            result = kb.build_index()

            # Verify index was built
            self.assertGreater(result["total_chunks"], 0,
                "build_index should produce chunks from the uploaded document")
            self.assertIn("john_doe_resume.txt", result["indexed_files"],
                "Resume file should appear in indexed_files")

            # Search for skills mentioned in the document
            search_results = kb.search("Python machine learning skills", top_k=3)
            self.assertGreater(len(search_results), 0,
                "search() should return results for a query matching document content")

            # Verify results contain relevant content
            all_content = " ".join(r.chunk.content.lower() for r in search_results)
            self.assertIn("python", all_content,
                "Search result content should contain the queried term 'python'")

            # Verify scores are non-negative
            for r in search_results:
                self.assertGreaterEqual(r.score, 0.0, "All search scores should be >= 0")

    def test_end_to_end_document_qa(self):
        """End-to-end test: write document → index → search → verify citations in context."""
        from backend.core.rag import KnowledgeBase

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Simulate a user's uploaded resume
            resume = tmp_path / "Alex_Rivera_Resume.md"
            resume.write_text(
                "# Alex Rivera — Product Manager\n\n"
                "## Contact\n"
                "Email: alex.rivera@email.com | LinkedIn: linkedin.com/in/alexrivera\n\n"
                "## Summary\n"
                "Experienced product manager with 8 years driving SaaS growth. "
                "Expert in agile methodology, user research, roadmap planning, and cross-functional leadership.\n\n"
                "## Experience\n"
                "**Senior Product Manager — TechFlow Inc** (2020–2024)\n"
                "- Led 0→1 launch of analytics dashboard used by 50,000+ users\n"
                "- Increased feature adoption by 35% through A/B testing and data analysis\n\n"
                "**Product Manager — StartupXYZ** (2016–2020)\n"
                "- Managed backlog of 200+ user stories for mobile app (iOS & Android)\n\n"
                "## Skills\n"
                "Product roadmap, JIRA, Confluence, SQL, user interviews, Figma, OKRs\n\n"
                "## Education\n"
                "MBA, Stanford Graduate School of Business, 2016\n"
                "B.S. Business Administration, UC Berkeley, 2014\n",
                encoding="utf-8"
            )

            kb = KnowledgeBase(workspace_dir=tmp_path)
            index_result = kb.build_index()
            self.assertGreater(index_result["total_chunks"], 0, "Index should have chunks")

            # Test Q&A queries
            queries_and_keywords = [
                ("What is Alex Rivera's work experience?", ["techflow", "startup", "product manager"]),
                ("What skills does Alex have?", ["sql", "jira", "figma", "roadmap"]),
                ("What is Alex's educational background?", ["stanford", "berkeley", "mba"]),
            ]

            for query, expected_keywords in queries_and_keywords:
                results = kb.search(query, top_k=3)
                self.assertGreater(len(results), 0,
                    f"Query '{query}' should return at least 1 result")

                # Format context as the production code would
                formatted = kb.format_retrieved_context(results)
                self.assertGreater(len(formatted["sources"]), 0,
                    f"Query '{query}' should include source citations")

                # Verify the source is Alex's resume
                source_paths = [s["relative_path"] for s in formatted["sources"]]
                self.assertTrue(
                    any("Alex_Rivera_Resume" in sp for sp in source_paths),
                    f"Query '{query}' should cite Alex's resume, got sources: {source_paths}"
                )

                # Verify content block contains at least one expected keyword
                context_lower = formatted["context_text"].lower()
                matched = [kw for kw in expected_keywords if kw in context_lower]
                self.assertGreater(len(matched), 0,
                    f"Context for '{query}' should contain one of {expected_keywords}, got: {context_lower[:200]}")


if __name__ == "__main__":
    unittest.main()

