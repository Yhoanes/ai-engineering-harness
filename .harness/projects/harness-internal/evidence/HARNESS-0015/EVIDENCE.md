# HARNESS-0015 Evidence

BUG:
HARDCODED_V1_0_0_EXPORT_TAG

OLD_FIELD:
tag_baseline

FINAL_FIELD:
release_tag

MANIFEST_FORMAT_VERSION_DECISION:
Retained "1" because Export Engine hasn't been officially released yet, so correcting the field name is considered part of its initial v1.1.0 release.

TAG_DISCOVERY:
Using `git tag --points-at HEAD` with subprocess structured arguments.

UNTAGGED_HEAD:
Emits `release_tag: null` (None in Python).

VERSION_TAG_MISMATCH:
Strict BLOCKED response. E2E verified.

MULTIPLE_TAG_POLICY:
Filters tags by SemVer `^v\d+\.\d+\.\d+$`. Resolves unambiguous mismatches, blocks if ambiguous.

PRODUCT_HARDCODE_SCAN:
Found no other hardcoded versions in `engine/export/**`.

TAGGED_E2E:
Verified extraction emits `v1.0.0` correctly for matching HEAD.

POST_TAG_COMMIT_E2E:
Verified clean untagged HEAD emits `release_tag: null`.

V1_1_0_E2E:
Verified `v1.1.0` is recognized accurately.

MISMATCH_E2E:
Verified blocking behavior for `VERSION_TAG_MISMATCH`.

REPRODUCIBILITY:
IDENTICAL DEVELOPMENT.zip and PORTABLE.zip outputs. (Manifest changes due to release_tag bugfix; HISTORY.bundle content equivalence unchanged).

HISTORY_BUNDLE:
PASS bundle verify.

SECURITY_REVIEW:
Command uses `subprocess.run(["git", "tag", "--points-at", "HEAD"], check=False)`. No shell execution, no user-input interpolation.

HARNESS_0014_PREEXISTING_SHA256:
98b200cb323d25f7b1f0862f20ec45da1ee716c364e40e641152af5b609d3421

HARNESS_0014_FINAL_SHA256:
98b200cb323d25f7b1f0862f20ec45da1ee716c364e40e641152af5b609d3421

HARNESS_0014_UNCHANGED:
YES

FULL_PYTEST:
454 passed, 2 skipped

RUFF:
PASS

V1/V5a/V6/V7/V8/V9/V5b:
PASS
