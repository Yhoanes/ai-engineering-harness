# Validation of HARNESS-0042

- **Objetivo**: Mejorar UX detectando la presencia de agy sin forzar su instalacion.
- **Mecanismo**: Get-Command agy -ErrorAction SilentlyContinue
- **Agy auto-install**: No se instala automáticamente.
- **Ausencia de agy**: No bloquea instalación y no cambia STATUS READY del Harness core.
- **Agy presente**:
  Antigravity CLI ........ PASS
- **Agy ausente**:
  Antigravity CLI ........ NOT INSTALLED
- **Notice**:
  Antigravity provider execution is unavailable until agy is installed
- **Network**: No añadido.
- **PATH**: No modificado.
- **-Check**: Conserva exit-code contract.
- **Tests**:
  - agy present: Sí
  - agy absent: Sí
  - no-auto-install: Sí
- **Installer tests**: 8
- **Suite**: 684 passed, 4 skipped
- **Collected**: 688
- **Ruff**: PASS
- **PowerShell syntax**: PASS (usando PowerShell Windows default)
- **Diagnostics**: READY
- **Task validator**: PASS
- **Authoritative loader**: PASS
- **Matrix validation**: PASS
- **Provider / Agy**: No provider real ejecutado ni agy real ejecutado durante esta tarea.
