# Installer and Bootstrap

This directory contains the cross-platform wrappers for the deterministic AI Engineering Harness diagnostic and installation engine.

## Windows Quickstart

From the extracted Harness root, double-click `INSTALAR.cmd`. It calls the secured
PowerShell bootstrap, preserves its exit code, and keeps the final status visible.

For terminals or automation, run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\install\setup.ps1"
```

*(Note: We do not permanently modify your execution policy or require administrator rights. The bypass flag is a one-time process scope setting for Windows if you encounter policy errors).*

The launcher does not install Python or acquire private-repository access. Python 3.11+
must already be available.

For full details on Check Mode, Repair Mode, and Development Mode, see [docs/installation.md](../docs/installation.md).
