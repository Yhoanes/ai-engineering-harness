# Installation Guide

The AI Engineering Harness uses a secure, portable, and reproducible bootstrap system. The installer wrapper coordinates local Python execution without making any persistent global changes to your system.

## Prerequisites

- **Python 3.11+** must be installed and available in your PATH.
- **Git** is required for history-bundle export and the full development test suite.
  A global Git `user.name` or `user.email` is not required.
- (Optional but recommended) Internet access for the first dependency installation, unless you have offline wheels configured.

**No Administrator Rights Required:** The bootstrap only uses local folders.

## Windows Installation

### Simple installation

From the root of the extracted Harness, double-click `INSTALAR.cmd`. The launcher:

- Resolves the Harness directory even when its path contains spaces.
- Runs the existing PowerShell bootstrap without changing the system execution policy.
- Preserves the bootstrap exit code and keeps the final result visible.

If it succeeds, you'll see `INSTALACION COMPLETADA: STATUS READY`. All dependencies
remain isolated in the local `.venv` directory, and the `projects/` directory is never
modified by the installer.

### PowerShell installation

The equivalent command for terminals and automation is:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\install\setup.ps1"
```

If it succeeds, you'll see a `STATUS: READY` report.

The installer does not download Python, clone a private repository, or grant GitHub
access. Those prerequisites must be satisfied before installation.

### Portable vs Development Mode

By default, the installer uses **Portable Mode** (`pip install .`), keeping your source tree isolated from the installed package.

If you are developing the Harness itself:
```powershell
.\install\setup.ps1 -Mode Development
```
This runs `pip install -e .[dev]` and links the codebase dynamically for live editing.

### Check and Repair Modes

To simply verify health without touching the environment:
```powershell
.\install\setup.ps1 -Check
```

If your environment is broken and you want to safely reinstall dependencies without deleting the local `.venv`:
```powershell
.\install\setup.ps1 -Repair
```

## Linux and macOS

A `setup.sh` is pending, but the core engine is fully cross-platform. You can manually bootstrap using:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install .
python -m engine.diagnostics
```

## Offline Reality

If your machine is fully disconnected from the internet and doesn't have a local PyPI cache, `pip` will fail. The diagnostics will safely catch this and return `DEPENDENCY_DOWNLOAD_MAY_BE_REQUIRED`. 
