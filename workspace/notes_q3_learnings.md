# Personal Engineering Notes: Q3 Learnings on Local Agents
**Author:** Alex Rivera  
**Last Updated:** September 2026  

---

## 1. Why Pure LLM Autonomy Fails in Local Environments
- LLMs given raw bash or code execution access hallucinate flags, delete files unintentionally, or fail silently.
- Solution: Limit the agent to a minimal, fixed whitelist of 5 deterministic Python functions (`list_files`, `read_file`, `search_documents`, `create_file`, `create_folder`).
- Never let the LLM generate code to be executed directly on the host OS.

---

## 2. The Power of Post-Action Verification
- LLMs often output "I have created the file" even when an exception occurred or disk permissions denied write access.
- An automated verification step (`verifier.py`) must independently inspect the filesystem to confirm:
  1. File exists at exact relative path
  2. Byte length > 0
  3. Content contains expected key sections
- Only when verification passes does the agent proceed or declare success.

---

## 3. Human-in-the-Loop as a Trust Primitive
- Read operations are harmless and can auto-run to gather context.
- Write/Mutating operations must pause and show the user what will be written before any disk touch.
- Users must have clear options: `Approve`, `Reject`, or `Modify`.
