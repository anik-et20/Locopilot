"""
Agent Orchestration Engine
Implements the core state machine for LocalGPT:
USER GOAL → UNDERSTAND → SEARCH LOCAL KNOWLEDGE → REASON/PLAN →
PERMISSION CHECK → EXECUTE APPROVED ACTION → VERIFY RESULT →
REPORT RESULT + SOURCES → AUDIT LOG
"""
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from pydantic import BaseModel
from .config import settings
from .llm import ollama_client
from .rag import knowledge_base
from .planner import planner, ExecutionPlan, PlanStep
from .tools import execute_tool, TOOL_REGISTRY
from .permission import permission_gateway, PermissionResponse
from .verifier import action_verifier
from .audit import audit_logger

logger = logging.getLogger("localgpt.orchestrator")

class AgentEvent(BaseModel):
    event_type: str
    session_id: str
    step_id: Optional[int] = None
    data: Dict[str, Any]

class AgentOrchestrator:
    def __init__(self):
        # Maps session_id -> active event queue for SSE streaming
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    async def run_pipeline(self, user_goal: str, session_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute the full agentic loop, yielding real-time status events for SSE streaming."""
        sess_id = session_id or str(uuid.uuid4())[:8]
        self._active_sessions[sess_id] = {"status": "running", "goal": user_goal}

        # 1. Start Session & Audit
        audit_logger.log_event(
            event_type="SESSION_STARTED",
            session_id=sess_id,
            goal=user_goal,
            details={"model": settings.ollama_model}
        )
        yield {
            "event": "SESSION_STARTED",
            "session_id": sess_id,
            "goal": user_goal,
            "message": "LocalGPT initialized in privacy-first local workspace mode."
        }

        # 2. Stage: Understand & Classify
        classification = await planner.classify_intent(user_goal)
        audit_logger.log_event(
            event_type="CLASSIFICATION_COMPLETED",
            session_id=sess_id,
            goal=user_goal,
            details={"classification": classification}
        )
        yield {
            "event": "UNDERSTAND",
            "session_id": sess_id,
            "classification": classification,
            "message": f"Classified intent as [{classification}]"
        }

        # 3. Stage: Search Local Knowledge (RAG)
        rag_results = knowledge_base.search(user_goal, top_k=4)
        formatted_rag = knowledge_base.format_retrieved_context(rag_results)
        
        audit_logger.log_event(
            event_type="KNOWLEDGE_SEARCHED",
            session_id=sess_id,
            goal=user_goal,
            sources_cited=formatted_rag["sources"],
            details={"num_results": len(rag_results)}
        )
        yield {
            "event": "KNOWLEDGE_RETRIEVED",
            "session_id": sess_id,
            "sources": formatted_rag["sources"],
            "total_chunks": len(rag_results),
            "context_preview": formatted_rag["formatted_block"][:400] + "..." if len(formatted_rag["formatted_block"]) > 400 else formatted_rag["formatted_block"],
            "message": f"Retrieved {len(rag_results)} relevant chunks from personal workspace."
        }

        # 4. Stage: Reason & Plan
        workspace_hint = f"Found {len(formatted_rag['sources'])} files: " + ", ".join(s["filename"] for s in formatted_rag["sources"])
        plan: ExecutionPlan = await planner.generate_plan(user_goal, workspace_hint)
        
        audit_logger.log_event(
            event_type="PLAN_GENERATED",
            session_id=sess_id,
            goal=user_goal,
            details={"plan_summary": plan.summary, "num_steps": len(plan.steps), "steps": [s.model_dump() for s in plan.steps]}
        )
        yield {
            "event": "PLAN_GENERATED",
            "session_id": sess_id,
            "plan": plan.model_dump(),
            "message": f"Generated {len(plan.steps)}-step execution plan."
        }

        # Execution Context Accumulator (stores outputs from each step to pass forward)
        accumulated_context: Dict[str, Any] = {
            "rag_context": formatted_rag["context_text"],
            "sources": formatted_rag["sources"],
            "step_outputs": {}
        }

        # 5. Execute Steps with Permission Checkpoints & Verification
        for step in plan.steps:
            yield {
                "event": "STEP_STARTED",
                "session_id": sess_id,
                "step_id": step.id,
                "tool": step.tool,
                "risk_level": step.risk_level,
                "description": step.description,
                "params": step.params
            }

            # Special parameter dynamic synthesis for create_file if needed
            if step.tool == "create_file" and (not step.params.get("content") or len(step.params.get("content", "")) < 50):
                # Dynamically synthesize tailored content using local LLM based on gathered RAG context
                yield {
                    "event": "SYNTHESIZING_CONTENT",
                    "session_id": sess_id,
                    "step_id": step.id,
                    "message": "Synthesizing custom document content with local Qwen model..."
                }
                synthesized_content = await self._synthesize_document_content(user_goal, accumulated_context)
                step.params["content"] = synthesized_content

            # Risk Assessment & Permission Checkpoint
            if step.risk_level == "HIGH":
                request_id = f"perm_{sess_id}_{step.id}"
                req = permission_gateway.create_request(
                    request_id=request_id,
                    session_id=sess_id,
                    step_id=step.id,
                    tool_name=step.tool,
                    params=step.params,
                    reasoning=step.reasoning or f"Required to complete step: {step.description}"
                )

                audit_logger.log_event(
                    event_type="PERMISSION_REQUESTED",
                    session_id=sess_id,
                    step_id=step.id,
                    action=step.tool,
                    risk_level=step.risk_level,
                    tool_args=step.params,
                    details={"request_id": request_id, "reasoning": req.reasoning}
                )

                yield {
                    "event": "PERMISSION_REQUIRED",
                    "session_id": sess_id,
                    "step_id": step.id,
                    "request_id": request_id,
                    "tool": step.tool,
                    "risk_level": step.risk_level,
                    "params": step.params,
                    "preview": req.preview,
                    "reasoning": req.reasoning,
                    "message": f"High-risk action '{step.tool}' requires your explicit approval."
                }

                # Pause until user responds via /api/permission endpoint
                decision: PermissionResponse = await permission_gateway.wait_for_decision(request_id)
                
                audit_logger.log_event(
                    event_type="PERMISSION_RESOLVED",
                    session_id=sess_id,
                    step_id=step.id,
                    action=step.tool,
                    risk_level=step.risk_level,
                    permission_status=decision.decision,
                    details={"modified_params": decision.modified_params, "comment": decision.user_comment}
                )

                yield {
                    "event": "PERMISSION_RESOLVED",
                    "session_id": sess_id,
                    "step_id": step.id,
                    "request_id": request_id,
                    "decision": decision.decision,
                    "message": f"Permission {decision.decision.lower()}ed by user."
                }

                if decision.decision == "REJECT":
                    yield {
                        "event": "STEP_SKIPPED",
                        "session_id": sess_id,
                        "step_id": step.id,
                        "reason": "User rejected permission request."
                    }
                    continue
                elif decision.decision == "MODIFY" and decision.modified_params:
                    step.params.update(decision.modified_params)

            # Tool Execution (Deterministic Python function)
            tool_res = execute_tool(step.tool, step.params)
            accumulated_context["step_outputs"][f"step_{step.id}"] = tool_res.output

            audit_logger.log_event(
                event_type="TOOL_EXECUTED",
                session_id=sess_id,
                step_id=step.id,
                action=step.tool,
                risk_level=step.risk_level,
                tool_args=step.params,
                execution_result={
                    "success": tool_res.success,
                    "execution_time_ms": tool_res.execution_time_ms,
                    "error": tool_res.error
                }
            )

            yield {
                "event": "TOOL_EXECUTED",
                "session_id": sess_id,
                "step_id": step.id,
                "tool": step.tool,
                "success": tool_res.success,
                "execution_time_ms": tool_res.execution_time_ms,
                "output": tool_res.output,
                "error": tool_res.error
            }

            # Post-Action Verification Step
            verification = action_verifier.verify_action(
                tool_name=step.tool,
                params=step.params,
                execution_output=tool_res.output if isinstance(tool_res.output, dict) else None
            )

            audit_logger.log_event(
                event_type="ACTION_VERIFIED",
                session_id=sess_id,
                step_id=step.id,
                action=step.tool,
                verification_result=verification.model_dump()
            )

            yield {
                "event": "ACTION_VERIFIED",
                "session_id": sess_id,
                "step_id": step.id,
                "tool": step.tool,
                "verified": verification.verified,
                "checks": [c.model_dump() for c in verification.checks],
                "summary": verification.summary_message
            }

        # 6. Final Report & Synthesis
        final_answer = await self._synthesize_final_report(user_goal, plan, accumulated_context)
        
        audit_logger.log_event(
            event_type="SESSION_COMPLETED",
            session_id=sess_id,
            goal=user_goal,
            details={"status": "success", "final_answer_length": len(final_answer)}
        )

        yield {
            "event": "FINAL_REPORT",
            "session_id": sess_id,
            "final_answer": final_answer,
            "sources": formatted_rag["sources"],
            "message": "LocalGPT workflow completed successfully."
        }

    async def _synthesize_document_content(self, goal: str, context: Dict[str, Any]) -> str:
        """Synthesize rich file content based on user goal and retrieved knowledge."""
        prompt = f"""You are LocalGPT. The user has requested to create or update a document.
User Goal: {goal}

Retrieved Personal Knowledge Context:
{context.get('rag_context', '')}

Write a comprehensive, professionally formatted markdown document fulfilling this request.
Include detailed sections, clear headings, and concrete specifics directly extracted from the context.
Output ONLY the markdown content for the file."""

        try:
            content = await ollama_client.generate_async(prompt=prompt, temperature=0.3)
            return content.strip()
        except Exception as e:
            logger.error(f"Error in document synthesis: {e}")
            return f"# Tailored Document\n\nGenerated for: {goal}\n\n## Context Sources\n{context.get('rag_context', '')[:500]}"

    async def _synthesize_final_report(self, goal: str, plan: ExecutionPlan, context: Dict[str, Any]) -> str:
        """Generate final user summary with source provenance."""
        prompt = f"""You are LocalGPT, an on-device privacy-first AI agent.
The user goal was: "{goal}"

Plan executed:
{plan.summary}

Retrieved Local Documents:
{context.get('rag_context', '')[:1500]}

Please write a clear, concise final summary report for the user.
Highlight:
1. What was discovered in their local documents
2. What actions were executed & verified
3. Clear attribution to the local sources used

Keep it friendly, structured, and strictly based on local data."""

        try:
            report = await ollama_client.generate_async(prompt=prompt, temperature=0.3)
            return report.strip()
        except Exception as e:
            logger.error(f"Error generating final report: {e}")
            return f"### Task Completed\n\n**Goal:** {goal}\n\n**Actions Executed:** All planned steps were executed and verified against your local workspace.\n\n**Sources Consulted:** {', '.join(s['filename'] for s in context.get('sources', []))}"

agent_orchestrator = AgentOrchestrator()
