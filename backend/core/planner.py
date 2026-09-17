"""
Agent Planner & Intent Classifier
Classifies user requests and decomposes complex goals into structured JSON action plans.
Enforces strict schema validation, deterministic tool boundaries, and auto-repair.
"""
import json
import re
import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from .config import settings
from .llm import ollama_client
from .tools import TOOL_REGISTRY

logger = logging.getLogger("localgpt.planner")

class PlanStep(BaseModel):
    id: int
    description: str
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "LOW"  # "LOW" or "HIGH"
    reasoning: str = ""
    expected_output: str = ""

class ExecutionPlan(BaseModel):
    goal: str
    classification: str  # QUESTION, SEARCH, ANALYSIS, GENERATION, ACTION, MULTI_STEP
    summary: str
    steps: List[PlanStep]

CLASSIFICATION_TYPES = [
    "QUESTION",       # Simple Q&A about workspace or facts
    "SEARCH",         # Retrieval/search query across documents
    "ANALYSIS",       # Comparing, evaluating, or extracting insights from documents
    "GENERATION",     # Synthesizing new content from workspace knowledge
    "ACTION",         # Creating files/folders
    "MULTI_STEP"      # Complex workflow combining search, reasoning, and creation
]

PLANNER_SYSTEM_PROMPT = f"""You are LocalGPT Planner, a privacy-first AI agent orchestrator for a personal digital workspace.
Your task is to break down the user's goal into a precise, minimal, ordered JSON execution plan.

You have access to EXACTLY 5 deterministic tools:
1. `list_files(subpath)` - [Risk: LOW] List files and folders in workspace.
2. `read_file(filepath)` - [Risk: LOW] Read a specific file (e.g. 'Alex_Rivera_Resume.md').
3. `search_documents(query, top_k)` - [Risk: LOW] RAG search over personal notes/reports.
4. `create_file(filepath, content)` - [Risk: HIGH] Create/write a file (e.g. 'output/tailored_application.md').
5. `create_folder(folderpath)` - [Risk: HIGH] Create a directory.

CRITICAL RULES:
- Never invent tools or run arbitrary code/shell commands.
- Read operations (list_files, read_file, search_documents) are LOW risk.
- Write operations (create_file, create_folder) are HIGH risk.
- High-risk operations must come AFTER gathering necessary context from low-risk tools.
- Output ONLY a single valid JSON object. No preamble, no conversational text outside the JSON.

Expected JSON schema:
{{
  "goal": "The user's goal",
  "classification": "QUESTION" | "SEARCH" | "ANALYSIS" | "GENERATION" | "ACTION" | "MULTI_STEP",
  "summary": "Short explanation of the plan",
  "steps": [
    {{
      "id": 1,
      "description": "Step title",
      "tool": "search_documents",
      "params": {{"query": "AI research experience"}},
      "risk_level": "LOW",
      "reasoning": "Retrieve relevant sections from personal workspace",
      "expected_output": "Context snippets"
    }},
    {{
      "id": 2,
      "description": "Create tailored application document",
      "tool": "create_file",
      "params": {{"filepath": "output/application.md", "content": "..."}},
      "risk_level": "HIGH",
      "reasoning": "Write finalized tailored result to workspace",
      "expected_output": "Saved application file"
    }}
  ]
}}
"""

def clean_json_text(text: str) -> str:
    """Extract and sanitize JSON from model output."""
    text = text.strip()
    # Remove markdown code block if present
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        text = match.group(1).strip()
    
    # Locate first '{' and last '}'
    first_brace = text.find('{')
    last_brace = text.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        text = text[first_brace:last_brace+1]
    
    return text

class AgentPlanner:
    def __init__(self):
        pass

    async def classify_intent(self, user_goal: str) -> str:
        """Classify user intent into one of the 6 standard categories."""
        prompt = f"""Classify this user request into exactly one category:
Options: {', '.join(CLASSIFICATION_TYPES)}

User Request: "{user_goal}"

Respond with ONLY the single category name in uppercase."""
        
        try:
            response = await ollama_client.generate_async(prompt, temperature=0.0)
            cleaned = response.strip().upper()
            for cat in CLASSIFICATION_TYPES:
                if cat in cleaned:
                    return cat
        except Exception as e:
            logger.warning(f"Classification LLM failed ({e}), falling back to heuristic.")
        
        # Heuristic fallback
        goal_lower = user_goal.lower()
        if any(w in goal_lower for w in ["create", "write", "generate and save", "make a file", "save to"]):
            if any(w in goal_lower for w in ["analyze", "review", "compare", "search", "read"]):
                return "MULTI_STEP"
            return "ACTION"
        elif any(w in goal_lower for w in ["search", "find", "look up", "retrieve"]):
            return "SEARCH"
        elif any(w in goal_lower for w in ["analyze", "compare", "evaluate", "gap"]):
            return "ANALYSIS"
        elif any(w in goal_lower for w in ["draft", "generate", "write"]):
            return "GENERATION"
        return "QUESTION"

    async def generate_plan(self, user_goal: str, workspace_context_hint: str = "") -> ExecutionPlan:
        """Generate a structured execution plan for the given goal using Qwen."""
        classification = await self.classify_intent(user_goal)
        
        prompt = f"""Goal: "{user_goal}"
Classification: {classification}
{f'Workspace context available: {workspace_context_hint}' if workspace_context_hint else ''}

Generate the structured JSON plan:"""

        for attempt in range(2):
            try:
                raw_output = await ollama_client.generate_async(
                    prompt=prompt,
                    system=PLANNER_SYSTEM_PROMPT,
                    format_json=True,
                    temperature=0.1
                )
                
                cleaned = clean_json_text(raw_output)
                plan_data = json.loads(cleaned)
                
                # Sanitize and validate steps
                validated_steps = []
                for idx, step_dict in enumerate(plan_data.get("steps", [])):
                    tool = step_dict.get("tool", "").strip()
                    if tool not in TOOL_REGISTRY:
                        # Auto-map known variations
                        if "search" in tool:
                            tool = "search_documents"
                        elif "read" in tool:
                            tool = "read_file"
                        elif "create_file" in tool or "write" in tool:
                            tool = "create_file"
                        elif "list" in tool:
                            tool = "list_files"
                        elif "folder" in tool or "dir" in tool:
                            tool = "create_folder"
                        else:
                            tool = "search_documents"
                    
                    risk = "HIGH" if tool in settings.high_risk_tools else "LOW"
                    validated_steps.append(PlanStep(
                        id=idx + 1,
                        description=step_dict.get("description", f"Execute {tool}"),
                        tool=tool,
                        params=step_dict.get("params", {}),
                        risk_level=risk,
                        reasoning=step_dict.get("reasoning", ""),
                        expected_output=step_dict.get("expected_output", "")
                    ))

                plan = ExecutionPlan(
                    goal=user_goal,
                    classification=plan_data.get("classification", classification),
                    summary=plan_data.get("summary", f"Plan to fulfill: {user_goal}"),
                    steps=validated_steps if validated_steps else self._build_default_steps(user_goal, classification)
                )
                return plan

            except Exception as e:
                logger.warning(f"Plan generation parse attempt {attempt+1} failed: {e}")

        # Resilient fallback plan generator
        return self._generate_heuristic_plan(user_goal, classification)

    def _build_default_steps(self, user_goal: str, classification: str) -> List[PlanStep]:
        """Build deterministic default steps based on classification."""
        if classification in ["ACTION", "MULTI_STEP"]:
            return [
                PlanStep(
                    id=1,
                    description="Search workspace for relevant background documents",
                    tool="search_documents",
                    params={"query": user_goal, "top_k": 4},
                    risk_level="LOW",
                    reasoning="Gather relevant personal resume, reports, or notes",
                    expected_output="Retrieved context chunks"
                ),
                PlanStep(
                    id=2,
                    description="Create target output document in workspace",
                    tool="create_file",
                    params={"filepath": "output/tailored_plan.md", "content": f"# Response Plan\n\nGenerated for: {user_goal}"},
                    risk_level="HIGH",
                    reasoning="Write tailored output file to workspace directory",
                    expected_output="Saved markdown file"
                )
            ]
        else:
            return [
                PlanStep(
                    id=1,
                    description="Search relevant workspace documents",
                    tool="search_documents",
                    params={"query": user_goal, "top_k": 4},
                    risk_level="LOW",
                    reasoning="Retrieve information from indexed workspace",
                    expected_output="Context and source citations"
                )
            ]

    def _generate_heuristic_plan(self, user_goal: str, classification: str) -> ExecutionPlan:
        """Heuristic plan generator guaranteeing 100% uptime for live demos."""
        steps = self._build_default_steps(user_goal, classification)
        return ExecutionPlan(
            goal=user_goal,
            classification=classification,
            summary=f"Automated multi-stage plan for '{user_goal}'",
            steps=steps
        )

planner = AgentPlanner()
