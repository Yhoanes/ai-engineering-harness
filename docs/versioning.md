# Semantic Versioning Strategy

The AI Engineering Harness follows Semantic Versioning strictly.
The `VERSION` file acts as the ultimate truth for the repository state.

## Version Recommendation
The `harness-evolution-advisor` predicts the required version bump for any `ExtensionProposal`:

### PATCH (1.x.y -> 1.x.y+1)
- Bugfixes that do not change functionality.
- Internal documentation updates.
- Refactoring that does not break interfaces.

### MINOR (1.x.y -> 1.x+1.0)
- Adding a new `Skill`.
- Adding a new `Specialist` or `Workflow` that doesn't replace core flows.
- Adding a new `Adapter` or `Provider`.
- Fully backward-compatible features.

### MAJOR (x.y.z -> x+1.0.0)
- Changes to `core/authority/authority-matrix.yaml` that alter fundamental permissions.
- Backward-incompatible changes to `TaskContract` schemas.
- Removing or heavily renaming core engine components.
- Adapter interface breaks.
