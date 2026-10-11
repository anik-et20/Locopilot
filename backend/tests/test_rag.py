"""
Tests for RAG Knowledge Engine
"""
import pytest
from pathlib import Path
from backend.core.rag import KnowledgeBase
from backend.core.config import settings

def test_rag_indexing_and_search():
    kb = KnowledgeBase(workspace_dir=settings.workspace_dir)
    res = kb.build_index()
    assert res["total_chunks"] > 0
    assert len(res["indexed_files"]) >= 3

    # Test search for workspace info
    results = kb.search("Project Alpha Technical Report or Research Intern", top_k=3)
    assert len(results) > 0
    assert any("Report" in r.chunk.filename or "Job" in r.chunk.filename for r in results)

    # Test formatted context
    formatted = kb.format_retrieved_context(results)
    assert len(formatted["sources"]) > 0
