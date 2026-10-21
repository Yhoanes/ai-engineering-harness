from engine.router import route_request


def test_dynamic_specialist_discovery(tmp_path):
    # 1. Create fake repo structure
    core_dir = tmp_path / "core"
    (core_dir / "specialists").mkdir(parents=True)
    (core_dir / "authority").mkdir(parents=True)
    (core_dir / "workflows" / "implement-task").mkdir(parents=True)

    # 2. Fake authority matrix
    auth_matrix = """
specialists:
  alien-engineer:
    read: { code: true }
    forbidden: []
"""
    (core_dir / "authority" / "authority-matrix.yaml").write_text(auth_matrix, encoding="utf-8")

    # 3. Fake workflow
    wf_yaml = """
id: implement-task
allowed_specialists:
  - alien-engineer
"""
    workflow_yaml_path = core_dir / "workflows" / "implement-task" / "workflow.yaml"
    workflow_yaml_path.write_text(wf_yaml, encoding="utf-8")

    # 4. Fake specialist
    alien_dir = core_dir / "specialists" / "alien-engineer"
    alien_dir.mkdir()
    alien_yaml = """
id: "alien-engineer"
display_name: "Alien Engineer"
description: "Builds extraterrestrial spaceships"
capabilities:
  - "warp drive"
  - "hyper sleep"
"""
    (alien_dir / "specialist.yaml").write_text(alien_yaml, encoding="utf-8")

    # 5. Test routing with keywords unique to the alien
    contract = {
        "status": "approved",
        "approval_status": "approved",
        "description": "implement warp drive for extraterrestrial spaceships"
    }
    decision = route_request("implement", task_contract=contract, repo_root=tmp_path)

    # Should discover and route to alien-engineer dynamically without Python code changes
    assert decision.workflow_id == "implement-task"
    assert decision.primary_specialist == "alien-engineer"
