# AI Engineering Harness Skills

This directory contains reusable, framework-agnostic execution capabilities known as **Skills**.

Skills represent actionable knowledge (how to do something repeatable) and are distinct from:
- **Specialists**: Agents/roles who invoke the skills.
- **Workflows**: Governed step-by-step processes.
- **Adapters**: Integrations that bridge the Harness to specific Hosts (Antigravity, Codex, OpenCode).

## Skill Structure
Each skill resides in its own isolated directory and MUST follow this neutral format:
```
skills/<skill-id>/
├── SKILL.md       # Declarative metadata frontmatter & description (source of truth)
├── scripts/       # Reusable executable logic
├── references/    # Documentation, context, or guides
└── assets/        # Static artifacts needed by the skill
```

## Execution Safety
**CRITICAL**: Scripts inside `skills/` are treated as **UNTRUSTED EXECUTABLE CAPABILITIES**. 
The Harness Extension Registry will read `SKILL.md` for metadata discovery but will NEVER execute scripts automatically.
Execution must be explicitly orchestrated by a governed Task Contract, subject to path containment and security review.
