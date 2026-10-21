from __future__ import annotations

from pathlib import Path

import pytest
import yaml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def valid_standard_task() -> dict:
    with (FIXTURES_DIR / "valid_task_standard.yaml").open() as f:
        return yaml.safe_load(f)


@pytest.fixture
def valid_light_task() -> dict:
    with (FIXTURES_DIR / "valid_task_light.yaml").open() as f:
        return yaml.safe_load(f)


@pytest.fixture
def invalid_task_missing_approval() -> dict:
    with (FIXTURES_DIR / "invalid_task_missing_approval.yaml").open() as f:
        return yaml.safe_load(f)


@pytest.fixture
def invalid_task_bad_transition() -> dict:
    with (FIXTURES_DIR / "invalid_task_bad_transition.yaml").open() as f:
        return yaml.safe_load(f)


@pytest.fixture
def valid_task_with_deviation() -> dict:
    with (FIXTURES_DIR / "valid_task_with_deviation.yaml").open() as f:
        return yaml.safe_load(f)


@pytest.fixture
def invalid_task_skip_no_reason() -> dict:
    with (FIXTURES_DIR / "invalid_task_skip_no_reason.yaml").open() as f:
        return yaml.safe_load(f)


@pytest.fixture
def sample_authority_matrix() -> dict:
    with (FIXTURES_DIR / "sample_authority_matrix.yaml").open() as f:
        return yaml.safe_load(f)
