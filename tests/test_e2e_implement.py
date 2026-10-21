"""E2E test: valid implementation with real agy.

This test exercises the FULL implement-task pipeline with a real
AntigravityCliExecutor and real agy invocation:

  Task Contract → Router → implement-task → WorktreeSandbox →
  agy real → physical file → get_diff → scope validation →
  validated → apply_to_main → applied → paused (governed review)

Scope enforcement against rogue files is tested deterministically
(without LLM dependency) in test_worktree_scope_integration.py.

Requires: HARNESS_RUN_ANTIGRAVITY_E2E=1
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(
    os.environ.get("HARNESS_RUN_ANTIGRAVITY_E2E") != "1",
    reason="E2E test requires HARNESS_RUN_ANTIGRAVITY_E2E=1",
)
def test_e2e_implement_valid():
    repo_root = Path.cwd()
    env = os.environ.copy()

    task_file = repo_root / "projects" / ".harness-internal" / "tasks" / "TASK-9998.yaml"
    evidence_dir = repo_root / "projects" / ".harness-internal" / "evidence" / "TASK-9998"
    valid_file = repo_root / "projects" / ".harness-internal" / "scratch" / "e2e_contador.html"

    task_content = """\
task_id: 'TASK-9998'
task_type: 'standard'
title: 'E2E Implement'
description: 'Implementation test'
project: '.harness-internal'
status: 'approved'
approval_status: 'approved'
approved_by: 'dummy'
approved_at: '2026-08-30T20:00:00Z'
approval_source: 'test'
approval_session_id: '123'
approval_receipt: 'abc'
acceptance_status: 'pending'
accepted_by: null
accepted_at: null
deviation: {documented: false, reason: null, authorized_by: null, mitigation_plan: null}
implementation_baseline:
  git_head: null
  working_tree_clean: null
  captured_at: null
  preexisting_untracked: []
scope:
  planned_paths:
    modify: ['projects/.harness-internal/scratch/e2e_contador.html']
    read: []
  allowed_actions:
    terminal: ['*']
    web: []
  forbidden_actions: []
assigned_workflow: 'implement-task'
assigned_specialists: ['frontend-engineer']
evidence:
  tests: {status: null}
  code_review: {status: null}
  security_review: {status: null}
postcheck: {status: null, run_at: null, findings: []}
approval_history: []
acceptance_history: []
created_at: '2026-08-30T20:00:00Z'
updated_at: '2026-08-30T20:00:00Z'
acceptance_criteria: []
"""

    def cleanup():
        if task_file.exists():
            task_file.unlink()
        if evidence_dir.exists():
            shutil.rmtree(evidence_dir)
        if valid_file.exists():
            valid_file.unlink()

    cleanup()

    try:
        # Setup approved Task Contract
        task_file.parent.mkdir(parents=True, exist_ok=True)
        task_file.write_text(task_content, encoding="utf-8")

        cmd = [
            ".venv\\Scripts\\python.exe",
            "-m",
            "engine.runner",
            "--project",
            ".harness-internal",
            "--task",
            "TASK-9998",
            "--intent",
            (
                "Implement this task. You MUST use the write_to_file tool to create "
                "projects/.harness-internal/scratch/e2e_contador.html. You MUST resolve "
                "its absolute path using your current working directory. The contents "
                "MUST be 'hello'. DO NOT explain anything, just call the tool."
            ),
            "--max-steps",
            "2",
            "--dangerously-skip-permissions",
        ]

        res = subprocess.run(
            cmd, cwd=repo_root, env=env, capture_output=True, text=True
        )
        print("E2E OUTPUT:")
        print(res.stdout)

        # Process must succeed
        assert res.returncode == 0

        # Full audit trail lifecycle
        assert "status='planned'" in res.stdout
        assert "status='sandbox_created'" in res.stdout
        assert "status='dispatched'" in res.stdout
        assert "status='executed'" in res.stdout
        assert "status='validated'" in res.stdout, "Must reach validated"
        assert "status='applied'" in res.stdout, "Must reach applied"
        assert "status='paused'" in res.stdout

        # Governed exit — NOT max_steps
        assert "Awaiting governed review" in res.stdout
        assert "max_steps" not in res.stdout.split("Awaiting governed review")[0].split(
            "status='paused'"
        )[-1]

        # Only implement-task, no discuss fallback
        assert "workflow='implement-task'" in res.stdout
        assert "workflow='discuss'" not in res.stdout

        # Physical file applied to main repo
        assert valid_file.exists(), "e2e_contador.html must be applied to main repo"

    finally:
        cleanup()
