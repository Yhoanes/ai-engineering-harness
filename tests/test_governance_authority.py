from pathlib import Path

import pytest
import yaml

from engine.execution.models import AccessMode, ScopedAccess
from engine.governance.authority import (
    get_execution_authority,
    load_authority_matrix,
    network_allows,
    path_allows,
    scope_allows,
    terminal_command_allows,
    validate_authority_matrix_data,
)


@pytest.fixture
def repo_root():
    return Path(__file__).parent.parent


def test_raw_matrix_bypass_closed():
    malformed = {
        "specialists": {
            "test-engineer": {
                "execution": {"modify_paths": {"mode": "unrestricted", "values": ["garbage"]}}
            }
        }
    }
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        get_execution_authority(malformed, "test-engineer")


def test_missing_specialist_explicit_failure():
    valid_matrix = {
        "specialists": {
            "test-engineer": {
                "execution": {
                    "read_paths": {"mode": "deny_all"},
                    "modify_paths": {"mode": "deny_all"},
                    "terminal_commands": {"mode": "deny_all"},
                    "network_allowed": False,
                }
            }
        }
    }
    with pytest.raises(ValueError, match="not found in Authority Matrix"):
        get_execution_authority(valid_matrix, "unknown-engineer")


def test_missing_execution_fails_schema():
    malformed = {"specialists": {"test-engineer": {"read": {"code": True}}}}
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        get_execution_authority(malformed, "test-engineer")


def test_terminal_command_allows():
    assert terminal_command_allows("git", "git")
    assert terminal_command_allows("git", "git diff")
    assert terminal_command_allows("git", "git status")
    assert not terminal_command_allows("git", "github")
    assert terminal_command_allows("git diff", "git diff --check")
    assert not terminal_command_allows("git diff", "git status")


def test_path_allows():
    assert path_allows("src/**", "src/main.py")
    assert path_allows("core", "core/main.py")
    assert path_allows("core", "core")
    assert not path_allows("core", "core_util")
    assert path_allows("*", "anything")


def test_scope_allows():
    max_deny = ScopedAccess(AccessMode.DENY_ALL, frozenset())
    assert scope_allows(max_deny, ScopedAccess(AccessMode.DENY_ALL, frozenset()), path_allows)
    assert not scope_allows(
        max_deny, ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["x"])), path_allows
    )  # noqa: E501
    assert not scope_allows(
        max_deny, ScopedAccess(AccessMode.UNRESTRICTED, frozenset()), path_allows
    )  # noqa: E501

    max_allow = ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["src/**"]))
    assert scope_allows(max_allow, ScopedAccess(AccessMode.DENY_ALL, frozenset()), path_allows)
    assert scope_allows(
        max_allow, ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["src/main.py"])), path_allows
    )  # noqa: E501
    assert not scope_allows(
        max_allow, ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["docs/"])), path_allows
    )  # noqa: E501
    assert not scope_allows(
        max_allow, ScopedAccess(AccessMode.UNRESTRICTED, frozenset()), path_allows
    )  # noqa: E501

    max_un = ScopedAccess(AccessMode.UNRESTRICTED, frozenset())
    assert scope_allows(max_un, ScopedAccess(AccessMode.DENY_ALL, frozenset()), path_allows)
    assert scope_allows(
        max_un, ScopedAccess(AccessMode.ALLOW_LIST, frozenset(["src/main.py"])), path_allows
    )  # noqa: E501
    assert scope_allows(max_un, ScopedAccess(AccessMode.UNRESTRICTED, frozenset()), path_allows)


def test_official_matrix_validation(repo_root):
    matrix = load_authority_matrix(repo_root)
    assert matrix is not None


def test_fixture_validation(repo_root):
    fixture_path = repo_root / "tests" / "fixtures" / "sample_authority_matrix.yaml"
    with open(fixture_path, encoding="utf-8") as f:
        matrix = yaml.safe_load(f)
    validate_authority_matrix_data(matrix)


def test_exact_migration_audit(repo_root):
    matrix = load_authority_matrix(repo_root)
    for _spec_id, spec in matrix["specialists"].items():
        if _spec_id == "harness-maintainer":
            continue
        historical = set(spec.get("modify", {}).get("scope", []))
        execution = spec.get("execution", {}).get("modify_paths", {})

        if not historical:
            assert execution["mode"] == "deny_all"
        else:
            assert execution["mode"] == "allow_list"
            assert set(execution["values"]) == historical


def test_read_and_terminal_deny_defaults(repo_root):
    matrix = load_authority_matrix(repo_root)
    for _spec_id, spec in matrix["specialists"].items():
        if _spec_id == "harness-maintainer":
            continue
        execution = spec.get("execution", {})
        assert execution.get("read_paths", {})["mode"] == "deny_all"
        assert execution.get("terminal_commands", {})["mode"] == "deny_all"


def test_router_regression(repo_root):
    from engine.router.specialist_selector import get_available_specialists

    available = get_available_specialists(repo_root)
    assert "harness-maintainer" in available
    assert available["harness-maintainer"]["profile"]["purpose"]


def test_schema_malformed_yaml(tmp_path):
    # A
    malformed_a = {
        "specialists": {
            "test": {
                "execution": {
                    "modify_paths": {"mode": "unrestricted", "values": ["core/**"]},
                    "read_paths": {"mode": "deny_all"},
                    "terminal_commands": {"mode": "deny_all"},
                    "network_allowed": False,
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        validate_authority_matrix_data(malformed_a)

    # B
    malformed_b = {
        "specialists": {
            "test": {
                "execution": {
                    "modify_paths": {"mode": "allow_list"},
                    "read_paths": {"mode": "deny_all"},
                    "terminal_commands": {"mode": "deny_all"},
                    "network_allowed": False,
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        validate_authority_matrix_data(malformed_b)

    # C
    malformed_c = {
        "specialists": {
            "test": {
                "execution": {
                    "modify_paths": {"mode": "invalid_mode"},
                    "read_paths": {"mode": "deny_all"},
                    "terminal_commands": {"mode": "deny_all"},
                    "network_allowed": False,
                }
            }
        }
    }
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        validate_authority_matrix_data(malformed_c)


def test_network_allows_truth_table():
    assert network_allows(maximum=False, requested=False) is True
    assert network_allows(maximum=False, requested=True) is False
    assert network_allows(maximum=True, requested=False) is True
    assert network_allows(maximum=True, requested=True) is True


def test_execution_authority_network_allowed(sample_authority_matrix):
    auth_arch = get_execution_authority(sample_authority_matrix, "backend-engineer")
    assert auth_arch.network_allowed is False

    auth_doc = get_execution_authority(sample_authority_matrix, "qa-engineer")
    assert auth_doc.network_allowed is False


def test_missing_network_allowed_rejected(sample_authority_matrix):
    # Remove network_allowed to trigger schema validation failure
    del sample_authority_matrix["specialists"]["backend-engineer"]["execution"]["network_allowed"]
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        get_execution_authority(sample_authority_matrix, "backend-engineer")


def test_invalid_network_allowed_rejected(sample_authority_matrix):
    sample_authority_matrix["specialists"]["backend-engineer"]["execution"]["network_allowed"] = (
        "true"
    )
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        get_execution_authority(sample_authority_matrix, "backend-engineer")

    sample_authority_matrix["specialists"]["backend-engineer"]["execution"]["network_allowed"] = (
        None
    )
    with pytest.raises(ValueError, match="Invalid Authority Matrix structure"):
        get_execution_authority(sample_authority_matrix, "backend-engineer")


def test_harness_maintainer_execution_ceiling(sample_authority_matrix):
    # If the fixture has harness-maintainer, test its ceiling
    if "harness-maintainer" in sample_authority_matrix["specialists"]:
        auth = get_execution_authority(sample_authority_matrix, "harness-maintainer")
        assert auth.read_paths.mode == AccessMode.UNRESTRICTED
        assert auth.terminal_commands.mode == AccessMode.UNRESTRICTED
        assert auth.network_allowed is True
        assert auth.modify_paths.mode == AccessMode.ALLOW_LIST


def test_harness_internal_metadata_scope(repo_root):
    from engine.governance.authority import path_allows
    matrix = load_authority_matrix(repo_root)
    execution = matrix["specialists"]["harness-maintainer"]["execution"]
    modify_values = execution["modify_paths"]["values"]

    # A. Nuevo pattern está presente
    assert ".harness/projects/harness-internal/**" in modify_values

    # B. Pattern viejo NO está presente
    assert "projects/.harness-internal/**" not in modify_values

    # C & D. Matches
    new_pattern = ".harness/projects/harness-internal/**"
    assert path_allows(new_pattern, ".harness/projects/harness-internal/tasks/HARNESS-0030.yaml")
    assert path_allows(
        new_pattern, ".harness/projects/harness-internal/evidence/HARNESS-0030/validation.md"
    )

    # E. Fails outside
    assert not path_allows(new_pattern, ".harness/projects/other-project/tasks/X.yaml")

    # F. Todos los demás modify patterns idénticos al baseline v1.12.0
    baseline_values = [
        "core/**",
        "engine/**",
        "adapters/**",
        "tests/**",
        "templates/**",
        "docs/**",
        "install/**",
        "packaging/**",
        "README.md",
        "VERSION",
        "skills/**",
        ".gitignore",
        "pyproject.toml",
        "dist/**",
        ".pytest_cache/**",
        ".ruff_cache/**",
        "**/__pycache__/**",
        "__pycache__/**"
    ]
    remaining = [v for v in modify_values if v != ".harness/projects/harness-internal/**"]
    assert set(remaining) == set(baseline_values)


def test_harness_maintainer_historical_execution_invariant(repo_root):
    matrix = load_authority_matrix(repo_root)
    spec = matrix["specialists"]["harness-maintainer"]

    historical = set(spec.get("modify", {}).get("scope", []))
    execution = set(spec.get("execution", {}).get("modify_paths", {}).get("values", []))

    assert historical == execution
