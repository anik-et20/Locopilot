import json
import re
import logging
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, List, Optional
from .config import settings
from .llm import ollama_client
from .agent_orchestrator import agent_orchestrator
from .chat_history import chat_history_db
from .rag import knowledge_base

logger = logging.getLogger("localgpt.chat")

class ChatManager:
    async def process_chat_message(self, message: str, history: List[Dict[str, str]], session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Process a chat message. 
        1. Classifies if the message requires workspace agent execution or normal chat.
        2. If agent: yields SSE events from agent_orchestrator and records to session history.
        3. If chat: retrieves relevant RAG context and streams response token-by-token.
        Guarantees that a terminal SSE event (CHAT_DONE, FINAL_REPORT, or ERROR) is always emitted.
        """
        sess_id = session_id or "default"
        terminal_event_emitted = False

        try:
            classification = await self._classify_intent(message, history)
            
            # Save user message to persistent session history
            chat_history_db.add_message(sess_id, "user", message)
            
            if classification == "AGENT":
                # Yield events from the agent orchestrator
                yield f"data: {json.dumps({'event': 'ROUTING', 'target': 'AGENT', 'session_id': sess_id, 'message': 'Workspace action/multi-step plan detected. Triggering agent pipeline...'})}\n\n"
                async for event_data in agent_orchestrator.run_pipeline(message, sess_id, history=history):
                    ev_type = event_data.get("event")
                    if ev_type in ["FINAL_REPORT", "ERROR"]:
                        terminal_event_emitted = True
                    if ev_type == "FINAL_REPORT":
                        final_ans = event_data.get("final_answer", "")
                        if final_ans:
                            chat_history_db.add_message(sess_id, "assistant", final_ans)
                    yield f"data: {json.dumps(event_data)}\n\n"
            else:
                # Get current workspace file inventory
                workspace_files = []
                for p in settings.workspace_dir.rglob("*"):
                    if p.is_file() and not any(part.startswith(".") for part in p.parts):
                        rel = p.relative_to(settings.workspace_dir).as_posix()
                        if not rel.startswith("test_output"):
                            workspace_files.append(rel)

                # Check if query or recent conversation mentions a specific workspace file
                target_specific_files = []
                for wf in workspace_files:
                    wf_name = Path(wf).name.lower()
                    wf_stem = Path(wf).stem.lower()
                    if wf_name in message.lower() or wf_stem in message.lower():
                        target_specific_files.append(wf)
                        agent_orchestrator.set_last_referenced_file(sess_id, wf)
                
                if not target_specific_files and history:
                    recent_hist = " ".join(h.get("content", "") for h in history[-4:]).lower()
                    for wf in workspace_files:
                        wf_name = Path(wf).name.lower()
                        wf_stem = Path(wf).stem.lower()
                        if wf_name in recent_hist or wf_stem in recent_hist:
                            target_specific_files.append(wf)
                            agent_orchestrator.set_last_referenced_file(sess_id, wf)

                # Retrieve workspace knowledge context for RAG augmentation
                rag_results = knowledge_base.search(message, top_k=4)
                formatted_rag = knowledge_base.format_retrieved_context(rag_results)
                
                # If specific target file was identified, ensure its content is directly loaded into context
                if target_specific_files:
                    target_rel = target_specific_files[0]
                    target_full_path = settings.workspace_dir / target_rel
                    direct_content = knowledge_base.load_document(target_full_path)
                    if direct_content:
                        direct_preview = direct_content[:1500]
                        if not formatted_rag["sources"]:
                            formatted_rag["sources"] = [{"filename": Path(target_rel).name, "relative_path": target_rel, "score": 1.0}]
                            formatted_rag["context_text"] = f"--- Document: {target_rel} ---\n{direct_preview}"
                        elif not any(s["relative_path"] == target_rel for s in formatted_rag["sources"]):
                            formatted_rag["sources"].insert(0, {"filename": Path(target_rel).name, "relative_path": target_rel, "score": 1.0})
                            formatted_rag["context_text"] = f"--- Document: {target_rel} ---\n{direct_preview}\n\n" + formatted_rag["context_text"]

                # Emit routing event
                yield f"data: {json.dumps({'event': 'ROUTING', 'target': 'CHAT', 'session_id': sess_id, 'message': 'Generating streaming response with local workspace knowledge...'})}\n\n"
                
                # If workspace knowledge was found, emit knowledge retrieval event with source chips
                if formatted_rag["sources"]:
                    yield f"data: {json.dumps({'event': 'KNOWLEDGE_RETRIEVED', 'session_id': sess_id, 'sources': formatted_rag['sources'], 'total_chunks': len(formatted_rag['sources']), 'message': f'Retrieved verified context from workspace documents.'})}\n\n"
                
                # Build comprehensive grounded system prompt with workspace inventory
                files_listing = "\n".join(f"- {f}" for f in sorted(workspace_files)) if workspace_files else "None"
                system_prompt = (
                    "You are LocalGPT, a privacy-first, on-device AI workspace assistant.\n"
                    "You have direct access to all files in the user's local workspace.\n\n"
                    f"CURRENT WORKSPACE FILES:\n{files_listing}\n\n"
                    "GROUNDING INSTRUCTIONS:\n"
                    "1. All files listed above exist in the workspace and are fully accessible to you. NEVER claim you do not have access to a file listed above.\n"
                    "2. The retrieved document context below provides verified excerpts from these files. Answer the user accurately based on this context.\n"
                    "3. Cite the relevant file names when answering.\n\n"
                    f"VERIFIED WORKSPACE CONTEXT:\n{formatted_rag['context_text']}"
                )
                
                prompt = self._format_chat_prompt(message, history)
                yield f"data: {json.dumps({'event': 'CHAT_START', 'session_id': sess_id})}\n\n"
                
                assistant_response = ""
                async for token in ollama_client.stream_generate(prompt=prompt, system=system_prompt, temperature=0.3):
                    assistant_response += token
                    yield f"data: {json.dumps({'event': 'CHAT_TOKEN', 'session_id': sess_id, 'token': token})}\n\n"
                    
                # Save assistant response to persistent session history
                chat_history_db.add_message(sess_id, "assistant", assistant_response)
                yield f"data: {json.dumps({'event': 'CHAT_DONE', 'session_id': sess_id})}\n\n"
                terminal_event_emitted = True

        except Exception as e:
            logger.error(f"Unhandled exception in chat processing: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'ERROR', 'session_id': sess_id, 'message': str(e)})}\n\n"
            terminal_event_emitted = True
        finally:
            if not terminal_event_emitted:
                # Fail-safe terminal event
                yield f"data: {json.dumps({'event': 'CHAT_DONE', 'session_id': sess_id})}\n\n"

    async def _classify_intent(self, message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Determines if the message needs multi-step agent execution (AGENT) or Q&A / chat (CHAT)."""
        m_lower = message.lower().strip()
        
        # 1. Broad phrase matching for AGENT routing (actions, file generation, conversions, retries, confirmations)
        agent_phrases = [
            "create file", "create a file", "generate file", "make a file", "create a pdf", "make a pdf",
            "make pdf", "generate pdf", "create pdf", "save to", "write to", "output/",
            "create folder", "tailored application", "gap analysis", "action plan",
            "modify file", "delete file", "run agent",
            # Follow-up and conversion phrasing
            "pdf format", "in a pdf", "in pdf", "as a pdf", "as pdf", "to a pdf", "to pdf",
            "provide the response in a pdf", "provide the response in pdf", "give in pdf", "give it in pdf",
            "make it a pdf", "make it pdf", "convert to pdf", "convert it to pdf", "convert that to pdf",
            "export as pdf", "export to pdf", "save as pdf", "turn it into a pdf", "turn into pdf",
            "try again", "same thing", "retry", "do the same", "now try again", "do it again",
            # Short confirmations for multi-step execution
            "yes do it", "do that", "do it", "summarize it", "summarize that", "make it", "create it", "go ahead"
        ]
        if any(phrase in m_lower for phrase in agent_phrases):
            return "AGENT"

        # 2. Check standalone 'pdf' word using regex
        if re.search(r'\bpdf\b', m_lower):
            if any(w in m_lower for w in ["make", "give", "provide", "create", "convert", "export", "in", "as", "format", "save", "it", "that", "this", "response", "again", "output"]):
                return "AGENT"

        # 3. Check conversion verbs with pronouns
        if any(verb in m_lower for verb in ["convert", "export", "reformat", "save"]) and any(ref in m_lower for ref in ["it", "that", "this", "file", "doc", "document", "response"]):
            return "AGENT"

        # 4. Check if recent conversation history discusses an action/document and user confirms
        if history:
            recent_text = " ".join(h.get("content", "") for h in history[-3:]).lower()
            if any(kw in recent_text for kw in ["output/", ".md", ".pptx", ".pdf", "application", "created", "presentation", "learnflow", "summary", "brief", "cover letter"]):
                if any(kw in m_lower for kw in ["pdf", "convert", "format", "again", "same", "export", "download", "now", "yes", "do it", "do that", "sure", "proceed", "summarize"]):
                    return "AGENT"

        # 5. Fast-path Q&A and briefing questions to CHAT (unless they ask to create/save a file or output)
        qa_starters = ["give me a brief", "brief me", "what is", "who is", "tell me about", "explain", "overview of", "describe", "how does", "summarize in chat"]
        has_file_write_action = any(w in m_lower for w in ["create file", "make a file", "save to", "write to", "output/", ".pdf", "as a pdf", "in pdf", "export", "convert"])
        if any(m_lower.startswith(q) for q in qa_starters) and not has_file_write_action:
            return "CHAT"

        # 6. Fast-path conversational greetings
        chat_keywords = ["hi", "hello", "hey", "who are you", "what can you do", "help", "thanks", "thank you", "bye"]
        if m_lower in chat_keywords or (len(m_lower.split()) <= 2 and not any(k in m_lower for k in ["pdf", "file", "make", "create", "convert", "again", "yes", "do"])):
            return "CHAT"

        # 7. LLM classification with conversation context
        history_summary = ""
        if history:
            recent_turns = history[-3:]
            history_summary = "\nRecent Conversation:\n" + "\n".join(f"{t.get('role')}: {t.get('content')[:120]}" for t in recent_turns)

        prompt = f"""You are a routing agent for a local AI workspace system.
Classify whether the user message requires AGENT (performing filesystem actions, file generation, creating/converting files, multi-step workspace workflows) or CHAT (informational Q&A, explanations, general questions).
{history_summary}

User message: "{message}"

Reply strictly with JSON: {{"route": "AGENT"}} or {{"route": "CHAT"}}
"""
        try:
            res = await ollama_client.generate_async(prompt, format_json=True, temperature=0.0, timeout=10.0)
            data = json.loads(res)
            return "AGENT" if data.get("route", "CHAT") == "AGENT" else "CHAT"
        except Exception as e:
            logger.warning(f"LLM routing fallback ({e})")
            fallback_agent_words = [
                "create", "write", "save", "make", "pdf", "convert", "export", "output/",
                "yes do it", "do that", "proceed", "do it again", "try again", "retry"
            ]
            return "AGENT" if any(w in m_lower for w in fallback_agent_words) else "CHAT"
            return "AGENT" if any(w in m_lower for w in fallback_agent_words) else "CHAT"

    def _format_chat_prompt(self, message: str, history: List[Dict[str, str]]) -> str:
        """Format chat history into a completion prompt for Ollama."""
        prompt_parts = []
        # Keep last 6 messages for conversation memory, trimming long historical outputs for fast inference
        for msg in (history or [])[-6:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "").strip()
            if len(content) > 350:
                content = content[:350] + "... [truncated for brevity]"
            prompt_parts.append(f"{role}: {content}")
        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)

chat_manager = ChatManager()
