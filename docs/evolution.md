# Harness Evolution

The AI Engineering Harness is designed to evolve itself through formal, governed Task Contracts. 

## The Harness Evolution Advisor
The `harness-evolution-advisor` is a specialized, READ-ONLY architect that helps you plan extensions to the Harness.
It does NOT execute changes. It analyzes requests and generates an `ExtensionProposal`.

## The Evolution Process
1. **IDEA**: You propose a change (e.g. "I want to add an OpenCode integration").
2. **CLASSIFY**: The Advisor determines if this is a Skill, Adapter, Provider, etc.
3. **IMPACT ANALYSIS**: The Advisor identifies the affected files, tests, and calculates SemVer impact.
4. **DESIGN**: The Advisor provides an `ExtensionProposal`.
5. **TASK PLAN**: A human issues a formal Task Contract (e.g. HARNESS-0012) incorporating the proposal.
6. **HUMAN APPROVAL**: The contract is approved.
7. **IMPLEMENT**: `harness-maintainer` executes the technical changes.
8. **TEST & REVIEW**: Quality and Security gates are passed.
9. **ACCEPT**: Human acceptance.
10. **VERSION DECISION**: A semantic version tag is generated based on the proposal.
11. **DISTRIBUTION**: The new portable package includes the capability.
