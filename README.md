# LocalGPT — Privacy-First AI Agent for Personal Workspaces

> **"Designed to keep AI processing local."**

LocalGPT is a privacy-first AI agent that operates over a user's personal digital workspace. Rather than relying on cloud models or granting an AI unrestricted system access, LocalGPT combines on-device inference, semantic document retrieval (RAG), a strict 5-tool deterministic sandbox, interactive human permission checkpoints for write actions, post-action verification, and an append-only audit trail.

---

## 🔁 The Core Execution Loop

```
USER GOAL → UNDERSTAND → SEARCH LOCAL KNOWLEDGE → REASON/PLAN →
PERMISSION CHECK → EXECUTE APPROVED ACTION → VERIFY RESULT →
REPORT RESULT + SOURCES → AUDIT LOG
```

---

## 🛠️ The 5 Deterministic Tools Whitelist

LocalGPT never executes arbitrary shell commands or LLM-generated code on the host OS. All actions are strictly whitelisted deterministic Python functions sandboxed inside `/workspace`:

| Tool | Risk Level | Description | Behavior |
| :--- | :--- | :--- | :--- |
| `list_files(subpath)` | `LOW` | Inspect directory tree within workspace | Auto-runs without prompt |
| `read_file(filepath)` | `LOW` | Read document content | Auto-runs without prompt |
| `search_documents(query)` | `LOW` | Semantic RAG search over personal files | Auto-runs without prompt |
| `create_file(filepath, content)` | `HIGH` | Write or overwrite file in workspace | **Requires User Approval** |
| `create_folder(folderpath)` | `HIGH` | Create subfolder in workspace | **Requires User Approval** |

---

## 🛡️ Safety & Trust Architecture

1. **Deterministic Sandboxing:** Path-traversal protection prevents access outside `/workspace`.
2. **Interactive Human-in-the-Loop Gateway:** When a high-risk tool (`create_file`, `create_folder`) is planned, execution pauses and yields a permission request with full reasoning and preview to the user.
3. **Automated Post-Action Verification:** After every write action, `verifier.py` independently inspects the filesystem to confirm inode creation, byte size > 0, and content integrity before declaring success.
4. **Append-Only Audit Logging:** Every goal, retrieved source, plan, permission decision, tool execution, and verification check is logged to `logs/audit_log.jsonl` with ISO timestamps.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally
- Pull the local Qwen model:
  ```bash
  ollama run qwen3:8b
  ```

### Installation
```bash
git clone <repo-url>
cd LocalPilot
pip install -r requirements.txt
```

### Run Server & Dashboard
```bash
python run.py
```
Open your browser at **`http://127.0.0.1:8000`**.

### Run Test Suite
```bash
python -m pytest backend/tests/
```

---

## 🎬 Hackathon Live Demo Scenario

**Demo Goal:**
> *"Review my resume (`Alex_Rivera_Resume.md`) and the job description (`Job_Description_AI_Research_Intern.md`), analyze skill gaps, and create a customized cover letter and tailored project action plan in `output/tailored_application.md`."*

**Live Flow Displayed in UI:**
1. **Understand:** Intent classified as `MULTI_STEP`.
2. **Search Local RAG:** Retrieves matching chunks from resume, JD, technical report, and notes with source badges.
3. **Structured Plan:** Generates ordered JSON plan.
4. **Permission Checkpoint:** UI triggers interactive gate showing preview of `output/tailored_application.md`.
5. **Human Approval:** User clicks `✓ Approve Action`.
6. **Deterministic Execution:** `create_file` executes in ~5ms.
7. **Verification:** Integrity engine checks disk file existence, size, and readability (`PASS`).
8. **Audit Log:** Real-time JSONL record logged and inspectable in the side drawer.
