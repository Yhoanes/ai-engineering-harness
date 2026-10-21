import re
import sys
from pathlib import Path

from engine.diagnostics.models import DiagnosticCheck, DiagnosticReport, DiagnosticStatus


def _get_python_requirement(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        return ">=3.11"

    content = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'requires-python\s*=\s*[\'"]([^\'"]+)[\'"]', content)
    if match:
        return match.group(1)
    return ">=3.11"


def _check_python_version(req: str) -> DiagnosticCheck:
    current = sys.version_info
    # Very basic parsing for >=X.Y
    status: DiagnosticStatus = "PASS"
    msg = f"Python {current.major}.{current.minor}.{current.micro}"
    remediation = None

    if req.startswith(">="):
        parts = req[2:].split(".")
        req_major = int(parts[0])
        req_minor = int(parts[1]) if len(parts) > 1 else 0
        if current.major < req_major or (current.major == req_major and current.minor < req_minor):
            status = "FAIL"
            msg = f"Python version {current.major}.{current.minor} is unsupported. Required: {req}"
            remediation = "PYTHON_VERSION_UNSUPPORTED"

    return DiagnosticCheck(
        id="PYTHON", status=status, message=msg, required=True, remediation=remediation
    )


def _check_version_file(repo_root: Path) -> tuple[DiagnosticCheck, str | None]:
    version_file = repo_root / "VERSION"
    if version_file.exists():
        version = version_file.read_text(encoding="utf-8").strip()
        return DiagnosticCheck(
            id="VERSION", status="PASS", message=f"Version found: {version}", required=True
        ), version
    return DiagnosticCheck(
        id="VERSION",
        status="FAIL",
        message="VERSION file missing",
        required=True,
        remediation="Restore the VERSION file in the repository root.",
    ), None


def _check_package_import() -> DiagnosticCheck:
    try:
        import engine  # noqa

        return DiagnosticCheck(
            id="PACKAGE_IMPORT",
            status="PASS",
            message="Package imported successfully",
            required=True,
        )
    except ImportError as e:
        return DiagnosticCheck(
            id="PACKAGE_IMPORT",
            status="FAIL",
            message=f"Failed to import 'engine': {e}",
            required=True,
            remediation="Run 'pip install .' inside the environment.",
        )


def _check_specialists(repo_root: Path) -> DiagnosticCheck:
    from engine.advisor.service import discover_specialists

    try:
        specs = discover_specialists(repo_root)
        if len(specs) > 0:
            return DiagnosticCheck(
                id="SPECIALISTS",
                status="PASS",
                message=f"{len(specs)} specialists discovered",
                required=True,
            )
        return DiagnosticCheck(
            id="SPECIALISTS", status="FAIL", message="No specialists discovered", required=True
        )
    except Exception as e:
        return DiagnosticCheck(id="SPECIALISTS", status="FAIL", message=str(e), required=True)


def _check_workflows(repo_root: Path) -> DiagnosticCheck:
    from engine.advisor.service import discover_workflows

    try:
        wfs = discover_workflows(repo_root)
        if len(wfs) > 0:
            return DiagnosticCheck(
                id="WORKFLOWS",
                status="PASS",
                message=f"{len(wfs)} workflows discovered",
                required=True,
            )
        return DiagnosticCheck(
            id="WORKFLOWS", status="FAIL", message="No workflows discovered", required=True
        )
    except Exception as e:
        return DiagnosticCheck(id="WORKFLOWS", status="FAIL", message=str(e), required=True)


def _check_specific_specialist(repo_root: Path, spec_id: str) -> DiagnosticCheck:
    from engine.advisor.service import discover_specialists

    try:
        specs = discover_specialists(repo_root)
        if any(s.get("id") == spec_id for s in specs):
            return DiagnosticCheck(
                id=spec_id.upper().replace("-", "_"),
                status="PASS",
                message=f"{spec_id} found",
                required=True,
            )
        return DiagnosticCheck(
            id=spec_id.upper().replace("-", "_"),
            status="FAIL",
            message=f"{spec_id} missing",
            required=True,
        )
    except Exception as e:
        return DiagnosticCheck(
            id=spec_id.upper().replace("-", "_"), status="FAIL", message=str(e), required=True
        )


def _check_project_manager() -> DiagnosticCheck:
    try:
        from engine.projects.manager import initialize_project  # noqa

        return DiagnosticCheck(
            id="PROJECT_MANAGER", status="PASS", message="Available", required=True
        )
    except ImportError:
        return DiagnosticCheck(
            id="PROJECT_MANAGER", status="FAIL", message="Missing project manager", required=True
        )


def _check_context_loader() -> DiagnosticCheck:
    try:
        from engine.context.loader import load_context  # noqa

        return DiagnosticCheck(
            id="CONTEXT_LOADER", status="PASS", message="Available", required=True
        )
    except ImportError:
        return DiagnosticCheck(
            id="CONTEXT_LOADER", status="FAIL", message="Missing context loader", required=True
        )


def _check_antigravity_integration(repo_root: Path) -> DiagnosticCheck:
    required_files = [
        ".agents/agents.md",
        ".agents/rules/harness-governance.md",
        ".agents/skills/harness-advisor/SKILL.md",
        ".agents/workflows/advisor.md",
        ".agents/workflows/new-project.md",
        ".agents/workflows/evolve-harness.md"
    ]

    missing_files = []
    for rel_path in required_files:
        if not (repo_root / rel_path).is_file():
            missing_files.append(rel_path)

    if not missing_files:
        return DiagnosticCheck(
            id="ANTIGRAVITY_INTEGRATION",
            status="PASS",
            message="Antigravity native integration components found",
            required=True
        )
    return DiagnosticCheck(
        id="ANTIGRAVITY_INTEGRATION",
        status="FAIL",
        message=f"Antigravity components missing: {', '.join(missing_files)}",
        required=True
    )


def run_diagnostics(repo_root: Path) -> DiagnosticReport:
    req = _get_python_requirement(repo_root)
    py_check = _check_python_version(req)

    ver_check, version = _check_version_file(repo_root)
    pkg_check = _check_package_import()

    checks = [py_check, ver_check, pkg_check]

    if pkg_check.status == "PASS":
        checks.append(_check_specialists(repo_root))
        checks.append(_check_workflows(repo_root))
        checks.append(_check_specific_specialist(repo_root, "general-advisor"))
        checks.append(_check_specific_specialist(repo_root, "harness-evolution-advisor"))
        checks.append(_check_project_manager())
        checks.append(_check_context_loader())
        checks.append(_check_antigravity_integration(repo_root))

    overall_status = "READY"
    if py_check.status == "FAIL":
        overall_status = "REQUIREMENT_MISSING"
    elif pkg_check.status == "FAIL":
        overall_status = "INSTALLATION_ERROR"
    elif any(c.status == "FAIL" and c.required for c in checks):
        overall_status = "CONFIGURATION_ERROR"

    return DiagnosticReport(
        harness_version=version,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        environment=sys.prefix,
        checks=checks,
        overall_status=overall_status,
    )
