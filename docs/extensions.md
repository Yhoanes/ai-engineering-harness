# Harness Extensions

The AI Engineering Harness ecosystem is extensible through strictly typed paradigms:

## 1. Specialist (Who)
**Path**: `core/specialists/<id>/`
An agent or role with a specific `authority_matrix` profile and system instructions. 

## 2. Workflow (Process)
**Path**: `core/workflows/<id>/`
A governed state-machine definition of how a task moves from inception to closure.

## 3. Skill (How)
**Path**: `skills/<id>/`
A reusable, standalone capability with declarative YAML frontmatter (`SKILL.md`) and optional untrusted execution scripts. 
Skills do not automatically execute.

## 4. Adapter (Integration)
**Path**: `adapters/<id>/`
The bridge between the Harness engine and an external Host environment (e.g. Antigravity).

*Note: Since v1.2.0, Antigravity integration is fully native. Advisors are registered in `.agents/`, and conversational interaction is provided via the `skills/harness-advisor` skill.*

## 5. Provider (Runtime)
The engine backend that runs AI models (e.g. OpenAI, Ollama). Decoupled from the Adapter.

## 6. Policy (Rule)
Static rules for validation or governance (e.g. repository hygiene).

## 7. Template (Scaffold)
**Path**: `templates/<id>/`
Reusable skeletons for initializing projects or files.

## 8. Validator (Gate)
**Path**: `engine/validators/`
Deterministic Python functions injected as control gates in workflows.
