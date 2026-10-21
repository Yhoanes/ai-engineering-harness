# Backup and Distribution Export

This document explains the official export mechanism for the AI Engineering Harness.

## Artifacts Generated

1. **DEVELOPMENT.zip**: Safe backup of the tracked development tree. Does NOT include `.git`, `.venv`, or user projects.
2. **PORTABLE.zip**: Standalone distribution built via `engine.distribution`. Does NOT include internal development history or user projects.
3. **HISTORY.bundle**: Git bundle containing all branches, tags, and commits.
4. **MANIFEST.json**: Deterministic metadata containing hashes, sizes, and versions.
5. **SHA256SUMS.txt**: Standard checksum file to verify the archives.

## Restore Procedure

### Development Restore
```bash
git clone AI-Engineering-Harness-<version>-HISTORY.bundle target-repo
cd target-repo
unzip ../AI-Engineering-Harness-<version>-DEVELOPMENT.zip
```
Note: You must extract the DEVELOPMENT.zip over the cloned repo to restore any untracked-but-internal files (if any were supported, though currently Development strictly uses tracked files, meaning the bundle contains them. The zip mainly acts as a flat-file safety net and exact snapshot).

### Portable Restore
Extract `PORTABLE.zip` to a new directory and run `install/setup.ps1` to bootstrap the environment.

## Export Restrictions
- Requires a clean `git status`.
- Destination must be strictly outside the source repository.
- Does not export secrets or machine-specific paths (except for internal historical evidence allowed in Development zip).
