import json
import logging
from typing import AsyncGenerator, Dict, Any, List, Optional
from .llm import ollama_client
from .agent_orchestrator import agent_orchestrator
from .chat_history import chat_history_db

logger = logging.getLogger("localgpt.chat")

class ChatManager:
    async def process_chat_message(self, message: str, history: List[Dict[str, str]], session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
        """
        Process a chat message. 
        1. Classifies if the message requires workspace agent execution or normal chat.
        2. If agent: yields SSE events from agent_orchestrator and records to history.
        3. If chat: yields SSE chat tokens and records to history.
        """
        classification = await self._classify_intent(message)
        
        # Save user message to persistent history
        chat_history_db.add_message("user", message)
        
        if classification == "AGENT":
            # Yield events from the agent orchestrator
            yield f"data: {json.dumps({'event': 'ROUTING', 'target': 'AGENT', 'message': 'Workspace request detected. Triggering agent pipeline...'})}\n\n"
            async for event_data in agent_orchestrator.run_pipeline(message, session_id):
                if event_data.get("event") == "FINAL_REPORT":
                    # Record final synthesized report to chat history
                    final_ans = event_data.get("final_answer", "")
                    if final_ans:
                        chat_history_db.add_message("assistant", final_ans)
                yield f"data: {json.dumps(event_data)}\n\n"
        else:
            # Yield normal chat response
            yield f"data: {json.dumps({'event': 'ROUTING', 'target': 'CHAT', 'message': 'Simple query detected. Answering conversationally...'})}\n\n"
            prompt = self._format_chat_prompt(message, history)
            yield f"data: {json.dumps({'event': 'CHAT_START'})}\n\n"
            
            assistant_response = ""
            async for token in ollama_client.stream_generate(prompt=prompt, system="You are LocalGPT, a helpful local AI assistant.", temperature=0.7):
                assistant_response += token
                yield f"data: {json.dumps({'event': 'CHAT_TOKEN', 'token': token})}\n\n"
                
            # Save assistant response to persistent history
            chat_history_db.add_message("assistant", assistant_response)
            yield f"data: {json.dumps({'event': 'CHAT_DONE'})}\n\n"

    async def _classify_intent(self, message: str) -> str:
        """Determines if the message needs workspace execution (AGENT) or just text response (CHAT)."""
        m_lower = message.lower()
        
        # Fast heuristic keyword routing for instantaneous responsiveness
        agent_keywords = [
            ".md", ".txt", ".pdf", ".py", ".json", "workspace", "file", "folder",
            "resume", "report", "notes", "cover letter", "job description",
            "review", "analyze", "synthesize", "search", "create", "write", "generate",
            "benchmark", "stanford", "gap", "audit", "sandbox", "verify", "pipeline"
        ]
        if any(kw in m_lower for kw in agent_keywords):
            return "AGENT"

        # If very short greeting/conversational phrase
        chat_keywords = ["hi", "hello", "hey", "who are you", "what can you do", "help", "thanks", "thank you", "bye"]
        if m_lower.strip() in chat_keywords or len(message.strip().split()) <= 2:
            return "CHAT"

        prompt = f"""You are a routing agent. 
Does this user message require interacting with local workspace files (e.g., reading files, creating files, searching documents, writing code, complex analysis on files)? 
Or is it a simple conversational query (e.g., greeting, general trivia, simple question not modifying files)?

Reply strictly with JSON: {{"route": "AGENT"}} or {{"route": "CHAT"}}

User message: "{message}"
"""
        try:
            res = await ollama_client.generate_async(prompt, format_json=True, temperature=0.0)
            data = json.loads(res)
            return "AGENT" if data.get("route", "CHAT") == "AGENT" else "CHAT"
        except Exception as e:
            logger.warning(f"LLM routing failed ({e}), falling back to default heuristic.")
            return "AGENT" if any(w in m_lower for w in ["file", "document", "read", "make", "find"]) else "CHAT"

    def _format_chat_prompt(self, message: str, history: List[Dict[str, str]]) -> str:
        """Format chat history into a completion prompt for Ollama."""
        prompt_parts = []
        # Keep last 5 messages for context
        for msg in history[-5:]:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content}")
        prompt_parts.append(f"User: {message}")
        prompt_parts.append("Assistant:")
        return "\n".join(prompt_parts)

chat_manager = ChatManager()
