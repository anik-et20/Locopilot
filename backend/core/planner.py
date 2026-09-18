"""
Agent Planner & Intent Classifier
Classifies user requests and decomposes complex goals into structured JSON action plans.
Enforces strict schema validation, deterministic tool boundaries, and auto-repair.
"""
import json
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ValidationError
from .config import settings
from .llm import ollama_client
from .tools import find_file_in_goal, TOOL_REGISTRY

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
2. `read_file(filepath)` - [Risk: LOW] Read a specific file (e.g. 'Alex_Rivera_Resume.md', 'LearnFlow_LMS_Presentation.pptx').
3. `search_documents(query, top_k)` - [Risk: LOW] RAG search over personal notes/reports.
4. `create_file(filepath, content)` - [Risk: HIGH] Create/write a file (e.g. 'output/tailored_application.md').
5. `create_folder(folderpath)` - [Risk: HIGH] Create a directory.

CRITICAL RULES:
- Never invent tools or run arbitrary code/shell commands.
- Read operations (list_files, read_file, search_documents) are LOW risk.
- Write operations (create_file, create_folder) are HIGH risk.
- High-risk operations must come AFTER gathering necessary context from low-risk tools.
- PDF RULE: If the user's goal explicitly asks to create/generate a PDF file (e.g. 'make a pdf', 'create cover_letter.pdf', 'generate PDF report'), ensure the target `filepath` in `create_file` ALWAYS ends with `.pdf` (e.g. 'output/cover_letter.pdf'). Otherwise use `.md` or `.txt`.
- CONVERSATION MEMORY & PRONOUN RESOLUTION: If recent conversation history is provided, resolve pronouns and short references ('it', 'that', 'yes do it', 'the same thing', 'summarize it') against what was just discussed — especially the last file name mentioned by the assistant or the user.
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

    async def classify_intent(self, user_goal: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """Classify user intent into one of the 6 standard categories."""
        goal_lower = user_goal.lower()

        # Fast heuristic classification
        if any(w in goal_lower for w in ["create", "write", "generate and save", "make a file", "save to", "output/", "yes do it", "do that"]):
            if any(w in goal_lower for w in ["analyze", "review", "compare", "search", "read", "gap", "job description"]):
                return "MULTI_STEP"
            return "ACTION"
        elif any(w in goal_lower for w in ["search", "find", "look up", "retrieve", "mention", "citations"]):
            return "SEARCH"
        elif any(w in goal_lower for w in ["synthesize", "analyze", "compare", "evaluate", "principles", "brief", "summarize"]):
            return "ANALYSIS"
        elif any(w in goal_lower for w in ["draft", "generate", "summarize", "write"]):
            return "GENERATION"

        history_context = ""
        if history:
            recent_turns = history[-3:]
            history_context = "\nRecent Conversation:\n" + "\n".join(f"{t.get('role')}: {t.get('content')[:120]}" for t in recent_turns)

        prompt = f"""Classify this user request into exactly one category:
Options: {', '.join(CLASSIFICATION_TYPES)}
{history_context}

User Request: "{user_goal}"

Respond with ONLY the single category name in uppercase."""
        
        try:
            response = await ollama_client.generate_async(prompt, temperature=0.0, timeout=30.0)
            cleaned = response.strip().upper()
            for cat in CLASSIFICATION_TYPES:
                if cat in cleaned:
                    return cat
        except Exception as e:
            logger.warning(f"Classification LLM failed ({e}), falling back to default.")
        
        return "QUESTION"

    async def generate_plan(self, user_goal: str, workspace_context_hint: str = "", history: Optional[List[Dict[str, str]]] = None) -> ExecutionPlan:
        """Generate a structured execution plan for the given goal using Qwen."""
        classification = await self.classify_intent(user_goal, history=history)
        
        history_summary = ""
        if history:
            recent_turns = history[-4:]
            history_summary = "\nRecent Conversation:\n" + "\n".join(f"{t.get('role')}: {t.get('content')[:120]}" for t in recent_turns)

        prompt = f"""Goal: "{user_goal}"
Classification: {classification}
{f'Workspace context available: {workspace_context_hint}' if workspace_context_hint else ''}
{history_summary}

Generate the structured JSON plan:"""

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

            if validated_steps:
                return ExecutionPlan(
                    goal=user_goal,
                    classification=plan_data.get("classification", classification),
                    summary=plan_data.get("summary", f"Plan to fulfill: {user_goal}"),
                    steps=validated_steps
                )
        except Exception as e:
            logger.warning(f"Plan generation parse attempt failed: {e}")

        # Resilient fallback plan generator
        return self._generate_heuristic_plan(user_goal, classification)

    def _build_default_steps(self, user_goal: str, classification: str) -> List[PlanStep]:
        """Build deterministic default steps based on classification."""
        is_pdf = bool(re.search(r'\bpdf\b', user_goal.lower()))
        ext = ".pdf" if is_pdf else ".md"
        matched_file = find_file_in_goal(user_goal)

        if classification in ["ACTION", "MULTI_STEP"]:
            if matched_file:
                true_stem = matched_file.split("/")[-1].split(".")[0]
                return [
                    PlanStep(
                        id=1,
                        description=f"Read {matched_file}",
                        tool="read_file",
                        params={"filepath": matched_file},
                        risk_level="LOW",
                        reasoning="Read the specific file the user mentioned",
                        expected_output=f"Content of {matched_file}"
                    ),
                    PlanStep(
                        id=2,
                        description="Create output document",
                        tool="create_file",
                        params={"filepath": f"output/{true_stem}_output{ext}", "content": ""},
                        risk_level="HIGH",
                        reasoning="Write processed content to workspace",
                        expected_output=f"Saved {ext} file"
                    )
                ]
            return [
                PlanStep(
                    id=1,
                    description="Search workspace for relevant documents",
                    tool="search_documents",
                    params={"query": user_goal, "top_k": 3},
                    risk_level="LOW",
                    reasoning="Gather relevant context from workspace",
                    expected_output="Retrieved context chunks"
                ),
                PlanStep(
                    id=2,
                    description="Create output document",
                    tool="create_file",
                    params={"filepath": f"output/result{ext}", "content": ""},
                    risk_level="HIGH",
                    reasoning="Write output to workspace",
                    expected_output=f"Saved {ext} file"
                )
            ]
        else:
            query = (
                matched_file.split("/")[-1].split(".")[0].replace("_", " ").replace("-", " ")
                if matched_file else user_goal
            )
            return [
                PlanStep(
                    id=1,
                    description="Search relevant workspace documents",
                    tool="search_documents",
                    params={"query": query, "top_k": 3},
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
