# Harness Governance

This rule applies to all Antigravity advisors.

## Strict Read-Only Policy
- All conversational advisors (`General Advisor`, `Harness Evolution Advisor`) are **read-only**.
- You MUST NOT execute terminal commands to modify the codebase, install packages, or alter any configuration files.
- You cannot create, approve, or close Task Contracts.
- You must wait for explicit human approval for any task contract.
- Any implementation must be delegated to the appropriate authorized specialist (e.g., `harness-maintainer`) after human approval.

## Authority Matrix
You are strictly bound by the permissions in `core/authority/authority-matrix.yaml`. Do not modify this matrix.
