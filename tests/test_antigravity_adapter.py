from __future__ import annotations

from pathlib import Path

import pytest

from adapters.antigravity import (
    AntigravityAdapter,
    AntigravityExecutionPlan,
    AntigravityRequest,
    AntigravityResponse,
)


class FakeExecutor:
    def __init__(self, raw_resp: str):
        self.raw_resp = raw_resp
        self.called = False

    def execute(self, plan: AntigravityExecutionPlan) -> AntigravityResponse:
        self.called = True
        return AntigravityResponse(raw_text=self.raw_resp)


@pytest.fixture
def repo(tmp_path: Path):
    (tmp_path / "core" / "specialists" / "general-advisor").mkdir(parents=True)
    (tmp_path / "core" / "specialists" / "general-advisor" / "prompt.md").write_text("advising")
    (tmp_path / "core" / "workflows" / "discuss").mkdir(parents=True)
    (tmp_path / "core" / "workflows" / "discuss" / "prompt.md").write_text("discussing")
    (tmp_path / "core" / "workflows" / "plan-task").mkdir(parents=True)
    (tmp_path / "core" / "workflows" / "plan-task" / "prompt.md").write_text("planning")
    (tmp_path / "core" / "specialists" / "orchestrator").mkdir(parents=True)
    (tmp_path / "core" / "specialists" / "orchestrator" / "prompt.md").write_text("orchestrating")

    (tmp_path / "projects" / "test").mkdir(parents=True)
    return tmp_path


def test_request_validation(repo: Path):
    adapter = AntigravityAdapter(repo)
    with pytest.raises(ValueError, match="project is required"):
        adapter.plan(AntigravityRequest(project="", user_input="hi"))
    with pytest.raises(ValueError, match="user_input cannot be empty"):
        adapter.plan(AntigravityRequest(project="test", user_input="   "))

    # Project regex
    for p in ["analista", "_harness-internal", "project-01", ".harness-internal"]:
        req = AntigravityRequest(project=p, user_input="hi")
        adapter.plan(req)  # Should pass

    for p in ["../x", "foo/bar", "foo\\bar", "/tmp/x", "C:\\temp", " ", "a b", ".harness-internal/.."]:  # noqa: E501
        with pytest.raises(ValueError, match="Invalid project format"):
            adapter.plan(AntigravityRequest(project=p, user_input="hi"))

    # Task ID regex
    for t in ["TASK-0001", "HARNESS-0001", "HARNESS-BOOTSTRAP-0001"]:
        req = AntigravityRequest(project="test", user_input="hi", task_id=t)
        adapter.plan(req)  # Should pass

    for t in ["TASK-1", "../TASK-0001", "TASK-0001/../../x", "/tmp/x", " ", ""]:
        with pytest.raises(
            ValueError, match="(Invalid task_id format|task_id cannot be empty string)"
        ):
            adapter.plan(AntigravityRequest(project="test", user_input="hi", task_id=t))


def test_load_task_contract_containment(repo: Path):
    adapter = AntigravityAdapter(repo)
    # create dummy project and task
    (repo / "projects" / "test" / "tasks").mkdir(parents=True)
    (repo / "projects" / "test" / "tasks" / "TASK-0001.yaml").write_text("status: approved")

    assert adapter._load_task_contract("test", "TASK-0001") == {"status": "approved"}

    # Try traversing outside of projects dir
    (repo / "projects").mkdir(exist_ok=True)
    (repo / "projects" / "outside.yaml").write_text("status: bad")

    # bypass normalization to test internal loader
    res = adapter._load_task_contract("test", "../outside")
    assert res is None


def test_discuss_routing(repo: Path):

    adapter = AntigravityAdapter(repo)
    print("CONTRACT:", adapter._load_task_contract("test", "TASK-0003"))
    req = AntigravityRequest(
project="test", user_input="ExplÃ­came cÃ³mo funciona esta parte")
    plan = adapter.plan(req)
    assert plan.route_decision.workflow_id == "discuss"
    assert plan.route_decision.primary_specialist == "general-advisor"
    assert "advising" in plan.specialist_prompt
    assert "discussing" in plan.workflow_prompt


def test_plan_task_routing(repo: Path):

    adapter = AntigravityAdapter(repo)
    print("CONTRACT:", adapter._load_task_contract("test", "TASK-0003"))
    req = AntigravityRequest(
project="test", user_input="Implementa la nueva feature")
    plan = adapter.plan(req)
    assert plan.route_decision.workflow_id == "plan-task"
    assert plan.route_decision.primary_specialist == "orchestrator"


def test_awaiting_approval_routing(repo: Path):
    (repo / "projects" / "test" / "tasks").mkdir(parents=True, exist_ok=True)
    (repo / "projects" / "test" / "tasks" / "TASK-0002.yaml").write_text(
        "status: awaiting_approval\napproval_status: pending"
    )
    (repo / "core" / "workflows" / "approve-task").mkdir(parents=True, exist_ok=True)
    (repo / "core" / "workflows" / "approve-task" / "prompt.md").write_text("approving")
    (repo / "core" / "specialists" / "harness-maintainer").mkdir(parents=True, exist_ok=True)
    (repo / "core" / "specialists" / "harness-maintainer" / "prompt.md").write_text("maintainer")


    adapter = AntigravityAdapter(repo)
    print("CONTRACT:", adapter._load_task_contract("test", "TASK-0003"))
    req = AntigravityRequest(

        project="test", user_input="please implement this", task_id="TASK-0002"
    )
    plan = adapter.plan(req)
    assert plan.route_decision.workflow_id == "approve-task"


def test_execute_requires_executor(repo: Path):

    adapter = AntigravityAdapter(repo)
    print("CONTRACT:", adapter._load_task_contract("test", "TASK-0003"))
    req = AntigravityRequest(
project="test", user_input="hi")
    with pytest.raises(ValueError, match="executor is explicitly required"):
        adapter.execute(req, None)  # type: ignore


def test_execute_success(repo: Path):

    adapter = AntigravityAdapter(repo)
    print("CONTRACT:", adapter._load_task_contract("test", "TASK-0003"))
    req = AntigravityRequest(
project="test", user_input="hi")
    executor = FakeExecutor('```json\n{"summary": "hello"}\n```')
    res = adapter.execute(req, executor)
    assert executor.called
    assert res.status == "success"
    assert res.output.structured_output == {"summary": "hello"}
    assert res.workflow == "discuss"

def test_implement_task_with_task_id_loads_contract(repo: Path):
    (repo / "projects" / "test" / "tasks").mkdir(parents=True, exist_ok=True)
    contract_yaml = (
        "status: approved\n"
        "approval_status: approved\n"
        "assigned_specialists: ['frontend-engineer']\n"
        "scope:\n"
        "  planned_paths:\n"
        "    modify: ['test_file.txt']"
    )
    task_path = repo / "projects" / "test" / "tasks" / "TASK-0003.yaml"
    task_path.write_text(contract_yaml)

    wf_dir = repo / "core" / "workflows" / "implement-task"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / "prompt.md").write_text("implementing")

    spec_dir = repo / "core" / "specialists" / "frontend-engineer"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "prompt.md").write_text("frontend dev")
    (spec_dir / "specialist.yaml").write_text("id: frontend-engineer")

    adapter = AntigravityAdapter(repo)
    req = AntigravityRequest(
        project="test", user_input="implement this", task_id="TASK-0003"
    )
    plan = adapter.plan(req)

    assert plan.route_decision.workflow_id == "implement-task"
    assert "test_file.txt" in plan.context_payload
    assert "status: approved" in plan.context_payload

def test_plan_with_assigned_specialist_and_context(repo: Path):
    from adapters.antigravity.models import AntigravityRequest
    from engine.context.models import ContextBundle
    adapter = AntigravityAdapter(repo)

    cb = ContextBundle(project="test", requested_level=0, loaded_level=0, sources={"mock": "mock"})
    req = AntigravityRequest(
        project="test",
        user_input="Implement it",
        assigned_specialist="general-advisor",
        context_bundle=cb
    )

    from unittest.mock import patch
    with patch('engine.orchestrator.orchestrator.load_context', return_value=cb) as mock_loader:
        plan = adapter.plan(req)
        mock_loader.assert_called_once()

    # Assert specialist was overridden
    assert plan.route_decision.primary_specialist == "general-advisor"
    # Assert context bundle was overridden
    assert plan.orchestrator_handoff.context_bundle is cb


def test_double_routing_bypassed_when_governed(tmp_path):
    from unittest.mock import patch

    from adapters.antigravity.adapter import AntigravityAdapter
    from adapters.antigravity.models import AntigravityRequest

    adapter = AntigravityAdapter(repo_root=tmp_path)
    request = AntigravityRequest(
        project="test-proj",
        user_input="intent",
        requested_workflow="implement-task",
        assigned_specialist="harness-maintainer"
    )

    with patch("adapters.antigravity.adapter.route_request") as mock_route, patch("adapters.antigravity.adapter.prepare_handoff"), patch("adapters.antigravity.adapter.build_prompt") as mock_build_fn:  # noqa: E501
            mock_build_fn.return_value = {"specialist_prompt": "", "workflow_prompt": "", "context_payload": "", "expected_output_contract": [], "final_prompt": ""}  # noqa: E501
            plan = adapter.plan(request)

            # route_request MUST NOT BE CALLED
            mock_route.assert_not_called()
            assert plan.route_decision.workflow_id == "implement-task"
            assert plan.route_decision.primary_specialist == "harness-maintainer"

def test_context_final_authority_override(tmp_path):
    from unittest.mock import patch

    from adapters.antigravity.adapter import AntigravityAdapter
    from adapters.antigravity.models import AntigravityRequest
    from engine.context.models import ContextBundle
    from engine.orchestrator.models import OrchestratorHandoff

    adapter = AntigravityAdapter(repo_root=tmp_path)

    # Context injected from orchestrator
    injected_bundle = ContextBundle(project="test-proj", requested_level=0, loaded_level=0, sources={"a.py": "a"}, missing_sources=[], content_sections={}, warnings=[])  # noqa: E501

    request = AntigravityRequest(
        project="test-proj",
        user_input="intent",
        requested_workflow="implement-task",
        assigned_specialist="harness-maintainer",
        context_bundle=injected_bundle
    )

    with patch("adapters.antigravity.adapter.prepare_handoff") as mock_loader, patch("adapters.antigravity.adapter.build_prompt") as mock_build_fn:  # noqa: E501
        mock_build_fn.return_value = {"specialist_prompt": "", "workflow_prompt": "", "context_payload": "", "expected_output_contract": [], "final_prompt": ""}  # noqa: E501
        # Loader loads something different (legacy behavior)
        legacy_bundle = ContextBundle(project="test-proj", requested_level=2, loaded_level=2, sources={"b.py": "b"}, missing_sources=[], content_sections={}, warnings=[])  # noqa: E501
        mock_loader.return_value = OrchestratorHandoff(project="test-proj", workflow="implement-task", primary_specialist="harness-maintainer", context_bundle=legacy_bundle)  # noqa: E501

        plan = adapter.plan(request)

        # The handoff bundle MUST be the injected one, NOT the legacy one
        assert plan.orchestrator_handoff.context_bundle == injected_bundle

def test_legacy_router_direct_fallback(tmp_path):
    from unittest.mock import patch

    from adapters.antigravity.adapter import AntigravityAdapter
    from adapters.antigravity.models import AntigravityRequest
    from engine.router.models import RouteDecision

    adapter = AntigravityAdapter(repo_root=tmp_path)
    request = AntigravityRequest(
        project="test-proj",
        user_input="intent",
        requested_workflow=None,
        assigned_specialist=None
    )

    with patch("adapters.antigravity.adapter.route_request") as mock_route, patch("adapters.antigravity.adapter.prepare_handoff"), patch("adapters.antigravity.adapter.build_prompt") as mock_build_fn:  # noqa: E501
        mock_route.return_value = RouteDecision("legacy-flow", "legacy-spec", 2, True, "reason")
        mock_build_fn.return_value = {"specialist_prompt": "", "workflow_prompt": "", "context_payload": "", "expected_output_contract": [], "final_prompt": ""}  # noqa: E501

        plan = adapter.plan(request)

        mock_route.assert_called_once()
        assert plan.route_decision.workflow_id == "legacy-flow"
        assert plan.route_decision.primary_specialist == "legacy-spec"

def test_partial_workflow_only(tmp_path):
    from unittest.mock import patch

    from adapters.antigravity.adapter import AntigravityAdapter
    from adapters.antigravity.models import AntigravityRequest
    from engine.router.models import RouteDecision

    adapter = AntigravityAdapter(repo_root=tmp_path)
    request = AntigravityRequest(
        project="test-proj",
        user_input="intent",
        requested_workflow="implement-task",
        assigned_specialist=None
    )

    with patch("adapters.antigravity.adapter.route_request") as mock_route, patch("adapters.antigravity.adapter.prepare_handoff"), patch("adapters.antigravity.adapter.build_prompt") as mock_build_fn:  # noqa: E501
        mock_route.return_value = RouteDecision("legacy-flow", "legacy-spec", 2, True, "reason")
        mock_build_fn.return_value = {"specialist_prompt": "", "workflow_prompt": "", "context_payload": "", "expected_output_contract": [], "final_prompt": ""}  # noqa: E501

        plan = adapter.plan(request)

        # We want to measure call count and final values explicitly
        assert mock_route.call_count == 1
        assert plan.route_decision.workflow_id == "legacy-flow"
        assert plan.route_decision.primary_specialist == "legacy-spec"

def test_partial_specialist_only(tmp_path):
    from unittest.mock import patch

    from adapters.antigravity.adapter import AntigravityAdapter
    from adapters.antigravity.models import AntigravityRequest
    from engine.router.models import RouteDecision

    adapter = AntigravityAdapter(repo_root=tmp_path)
    request = AntigravityRequest(
        project="test-proj",
        user_input="intent",
        requested_workflow=None,
        assigned_specialist="harness-maintainer"
    )

    with patch("adapters.antigravity.adapter.route_request") as mock_route, patch("adapters.antigravity.adapter.prepare_handoff"), patch("adapters.antigravity.adapter.build_prompt") as mock_build_fn:  # noqa: E501
        mock_route.return_value = RouteDecision("legacy-flow", "legacy-spec", 2, True, "reason")
        mock_build_fn.return_value = {"specialist_prompt": "", "workflow_prompt": "", "context_payload": "", "expected_output_contract": [], "final_prompt": ""}  # noqa: E501

        plan = adapter.plan(request)

        assert mock_route.call_count == 1
        assert plan.route_decision.workflow_id == "legacy-flow"
        assert plan.route_decision.primary_specialist == "harness-maintainer"
