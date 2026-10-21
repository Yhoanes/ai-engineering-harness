# HARNESS-0010 Evidence

## 1. Implementation Baseline
- **git_head**: 129b0c3d5d7f05060e68ffea9f818d9670babab5
- **working_tree_clean**: true
- **preexisting_untracked**: []

## 2. Files Changed
- `projects/.harness-internal/tasks/HARNESS-0010.yaml` (M)
- `packaging/distribution-manifest.yaml` (M)
- `core/specialists/harness-evolution-advisor/specialist.yaml` (New)
- `core/specialists/harness-evolution-advisor/prompt.md` (New)
- `engine/evolution/__init__.py`, `models.py`, `registry.py`, `service.py`, `versioning.py` (New)
- `skills/README.md`, `skills/_template/SKILL.md` (New)
- `docs/evolution.md`, `docs/extensions.md`, `docs/versioning.md` (New)
- `tests/test_evolution_service.py`, `tests/test_extension_registry.py`, `tests/test_skill_structure.py` (New)

## 3. Specialist Validation
`harness-evolution-advisor` created as a READ-ONLY specialist per schema. Cannot execute implementations.

## 4. Extension Classifications
- `classify_extension_request` maps requests to SPECIALIST, WORKFLOW, SKILL, ADAPTER, PROVIDER, POLICY, TEMPLATE, VALIDATOR.

## 5. Skill Safety
`ExtensionRegistry` performs metadata-only discovery without executing scripts. Unused `skills/_template` handled properly.

## 6. Self-Modification Test
`test_evolution_service_proposal_self_mod` confirmed that any attempt to modify `harness-evolution-advisor` flags `governance_changes_required=True`.

## 7. Authority Gap Test
`EvolutionService` reports authority gaps (e.g. `skills/**`) to the `ExtensionProposal`.

## 8. Portable Build
Tested via `build_distribution()`.
- `skills/` is present in the uncompressed distribution layout.
- `harness-evolution-advisor` correctly enumerated during portable evaluation.

## 9. General Advisor Evolution Routing Actual
- `GENERAL_ADVISOR_EVOLUTION_ROUTING: GAP_DETECTED` 
- Dynamic semantic recommendation requires LLM inference or an updated router, which currently defaults to `discuss` with `general-advisor`.

## 10. Security Review
- Pass: No execute vectors from untrusted Skill parsing.
- Pass: No path traversal from Extension ID validation.
- Pass: Evolution Advisor cannot modify Authority Matrix or write files.

## 11. V1 / V5a / V6 / V7 / V5b
All passed. Zero out-of-scope files detected.

## 12. Blockers
- **Legacy Test Failure**: `tests/test_specialists.py` (`test_ac01_exactly_18_specialists` and `test_exactly_36_specialist_files`) fails because it hardcodes the number of specialists to 18 (now 19). Modifying it was blocked by `V5b` scope constraints.

## 13. Human-Authorized Scope Amendment
- **SCOPE_AMENDMENT**: `tests/test_specialists.py` added via explicit Task Contract update to remove obsolete fixed specialist-count assumptions.
- **LEGACY_FIXED_COUNT_TESTS**: REMOVED_AS_OBSOLETE_INVARIANT
- **SPECIALIST_DISCOVERY_TEST**: PASS (Validates dynamic discovery of baseline + harness-evolution-advisor).
- **SPECIALIST_STRUCTURE_TEST**: PASS (Validates structure of every discovered directory).

## 14. Real Advisor and Quality Metrics
- **GENERAL_ADVISOR_REAL_TEST**: Tested deterministic API (`get_general_guidance`). Result: Hardcoded recommendation of `["general-advisor"]`.
- **GENERAL_ADVISOR_EVOLUTION_ROUTING**: GAP_DETECTED
- **GENERAL_ADVISOR_CHANGE_REQUIRED**: YES
- **ROUTER_DIRECT_EVOLUTION_ROUTING**: NOT_IMPLEMENTED_BY_DESIGN
- **FULL_PYTEST**: 437 passed, 2 skipped, 0 failed.
- **RUFF_CHECK**: PASS (0 errors).
- **RUFF_FORMAT**: PASS.

## 15. General Advisor Intent Classification
- **GENERAL_ADVISOR_SCOPE_AMENDMENT**: PASS (Authorized for `engine/advisor/**` and `tests/test_advisor_service.py`).
- **GENERAL_ADVISOR_BACKWARD_COMPATIBILITY**: PASS (`get_general_guidance` is unchanged and all original tests pass).
- **GENERAL_ADVISOR_EVOLUTION_ROUTING**: PASS (Implemented `get_guidance_for_request` to detect intent and route to `harness-evolution-advisor`).
- **GENERAL_ADVISOR_PROJECT_FALSE_POSITIVE**: PASS (Negative checks ensure project requests like "add authentication" don't trigger the Evolution Advisor).
- **EVOLUTION_ADVISOR_DISCOVERY**: PASS (Dynamically checked via `discover_specialists` before recommending).
- **EVOLUTION_ADVISOR_ABSENCE_HANDLING**: PASS (If uninstalled, returns blocker `EVOLUTION_ADVISOR_NOT_INSTALLED`).
- **ROUTER_CHANGE_REQUIRED**: NO (Intent classification sits above the Router, acting as an intent gateway via the public API).

## 16. Final Quality Metrics
- **FULL_PYTEST**: 437 passed, 2 skipped, 0 failed.
- **RUFF_CHECK**: PASS (0 errors).
- **RUFF_FORMAT**: PASS.
- **PORTABLE_ADVISOR_ROUTING**: PASS (Confirmed in `dist_temp`).
- **SECURITY_REVIEW**: PASS (Zero execution vectors, catalog-derived existence, no write access).

## 17. Final Evidence

FINAL_STATUS:
completed

ACCEPTANCE_STATUS:
passed

ACCEPTED_BY:
Yhoanes

ACCEPTED_AT:
2026-08-29T07:57:06-04:00

EVOLUTION_ADVISOR:
PASS

EVOLUTION_ENGINE:
PASS

SKILLS_FOUNDATION:
PASS

SKILL_DISCOVERY:
METADATA_ONLY

SKILL_SCRIPT_EXECUTION:
BLOCKED_BY_DESIGN

EXTENSION_TYPES:
8

GENERAL_ADVISOR_BACKWARD_COMPATIBILITY:
PASS

GENERAL_ADVISOR_EVOLUTION_ROUTING:
PASS

GENERAL_ADVISOR_PROJECT_FALSE_POSITIVE:
PASS

EVOLUTION_ADVISOR_DISCOVERY:
PASS

EVOLUTION_ADVISOR_ABSENCE_HANDLING:
PASS

ROUTER_CHANGE_REQUIRED:
NO

ADAPTER_CONTRACT:
DESIGN_PENDING

PROVIDER_RUNTIME:
NOT_IMPLEMENTED_BY_DESIGN

SELF_MODIFICATION_CONTROL:
PASS

AUTHORITY_ESCALATION_CONTROL:
PASS

SEMVER_RECOMMENDATION:
PASS

PORTABLE_SKILLS:
PASS

PORTABLE_EVOLUTION_ADVISOR:
PASS

DEVELOPMENT_IMPORT_LEAKAGE:
NONE

FULL_PYTEST:
437 passed, 2 skipped, 0 failed

RUFF_CHECK:
PASS

RUFF_FORMAT:
PASS

CODE_REVIEW:
PASS

SECURITY_REVIEW:
PASS

V4:
PASS

V8:
PASS

V9:
PASS

V5B:
PASS

V2_IN_PROGRESS_TO_COMPLETED:
PASS

BLOCKERS:
NONE
