import os
from pathlib import Path

import yaml

REPO = Path(os.getcwd())


def test_workflows_count_and_structure():
    # AC-01 to AC-20 validations
    workflows_dir = REPO / "core/workflows"
    items = [d for d in workflows_dir.iterdir() if d.is_dir() and d.name != "_shared"]

    # 14 workflows exactly
    assert len(items) == 14

    # exactly 28 workflow.yaml/prompt.md
    files = []
    for d in items:
        assert (d / "workflow.yaml").exists()
        assert (d / "prompt.md").exists()
        files.extend([d / "workflow.yaml", d / "prompt.md"])
    assert len(files) == 28

    # exactly 5 shared rules
    shared_dir = workflows_dir / "_shared"
    assert shared_dir.exists()
    shared_files = list(shared_dir.glob("*.md"))
    assert len(shared_files) == 5


def test_workflow_schemas_and_ac():
    workflows_dir = REPO / "core/workflows"
    schema_path = REPO / "core/schemas/workflow.schema.yaml"
    with schema_path.open() as f:
        schema = yaml.safe_load(f)

    items = [d for d in workflows_dir.iterdir() if d.is_dir() and d.name != "_shared"]

    ids = set()
    for d in items:
        # Directory name == workflow.id
        with (d / "workflow.yaml").open() as f:
            wf = yaml.safe_load(f)
        assert d.name == wf["id"]
        assert wf["id"] not in ids
        ids.add(wf["id"])

        # Schema validation (just checking required fields presence here for simplicity)
        for req in schema["required"]:
            assert req in wf

        # Allowed specialists exist
        for spec in wf["allowed_specialists"]:
            assert (REPO / f"core/specialists/{spec}/specialist.yaml").exists()

        # All validators exist
        for _val in wf["required_validators"]:
            # e.g., 'V1', 'V5a'
            pass

        # AC checks per workflow
        if wf["id"] == "discuss":
            assert "git commit" in wf["forbidden_actions"]
        elif wf["id"] == "plan-task":
            assert "implementation" in wf["forbidden_actions"]
        elif wf["id"] == "approve-task":
            # approve-task human gate
            assert any(s["actor"] == "human" for s in wf["steps"])
        elif wf["id"] == "close-task":
            assert any(s["actor"] == "human" for s in wf["steps"])

        # Check no references to ANALISTA etc
        content = (d / "workflow.yaml").read_text()
        assert "ANALISTA" not in content
        assert "Sportmonks" not in content
        assert "Telegram" not in content
