# Google Antigravity Integration

The AI Engineering Harness includes native integration with Google Antigravity (v1.2.0+). 

## Getting Started
1. Open the repository root (`C:\ai-engineering-harness`) as a workspace in Antigravity.
2. Antigravity will automatically load the local agents, rules, and workflows from the `.agents/` folder.
3. No credentials or global configs are required inside the repository; Antigravity handles the runtime securely.

## Native Slash Commands
You can trigger these commands directly in your Antigravity chat:
- `/advisor`: Converse with the General Advisor to explore ideas or architectures.
- `/new-project`: Scaffold a new project within the harness.
- `/evolve-harness`: Create formal Extension Proposals via the Harness Evolution Advisor.

## Security and Governance
- **Read-Only**: All Antigravity conversational advisors operate in strict read-only mode to prevent accidental damage.
- **Human Gates**: Any actionable work recommended by the advisors must be formalized into a Task Contract. An authorized human must explicitly approve the contract before automated specialists (e.g. `harness-maintainer`) can execute file modifications.
