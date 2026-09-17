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
        2. If agent: yields SSE events from agent_orchestrator.
        3. If chat: yields SSE chat tokens.
        """
        classification = await self._classify_intent(message)
        
        if classification == "AGENT":
            # Yield events from the agent orchestrator
            yield f"data: {json.dumps({'event': 'ROUTING', 'target': 'AGENT', 'message': 'Complex request detected. Triggering workspace agent pipeline...'})}\n\n"
            async for event_data in agent_orchestrator.run_pipeline(message, session_id):
                yield f"data: {json.dumps(event_data)}\n\n"
        else:
            # Save user message to persistent history
            chat_history_db.add_message("user", message)

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
        prompt = f"""You are a routing agent. 
Does this user message require interacting with the local workspace files (e.g., reading files, creating files, searching documents, writing code, complex analysis on files)? 
Or is it a simple conversational query (e.g., weather, greeting, general knowledge, simple coding question not modifying files)?

Reply strictly with JSON: {{"route": "AGENT"}} or {{"route": "CHAT"}}

User message: "{message}"
"""
        try:
            res = await ollama_client.generate_async(prompt, format_json=True, temperature=0.0)
            data = json.loads(res)
            return "AGENT" if data.get("route", "CHAT") == "AGENT" else "CHAT"
        except Exception as e:
            logger.error(f"Routing error: {e}")
            # Fallback heuristic
            m_lower = message.lower()
            if any(w in m_lower for w in ["file", "folder", "read", "workspace", "analyze", "create", "search"]):
                return "AGENT"
            return "CHAT"

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
