# HARNESS-0025 Validation

## Objetivo
Introduce Harness Metadata Path Abstraction. Crear un resolver central (`MetadataPaths`) para abstraer las rutas de metadata de `projects/<project>/...` sin cambiar archivos físicos.

## Archivos Modificados
- `core/context/metadata_paths.py` (Nuevo)
- `tests/test_metadata_paths.py` (Nuevo)
- `engine/context/loader.py`
- `engine/validators/validate_allowed_paths_post.py`
- `adapters/antigravity/adapter.py`
- `adapters/antigravity/autonomous_runner.py`
- `tests/test_context_loader.py`
- `tests/test_autonomous_runner.py`
- `projects/.harness-internal/tasks/HARNESS-0025.yaml`

## Componentes
- **MetadataPaths introducido**: Gestiona únicamente la metadata (`task_contract`, `proposal`, `evidence_dir`, `audit_trail`). NO resuelve ni gestiona `workspace_root`.
- **Validaciones centralizadas**: `is_valid_project_id`, `is_valid_task_id`, `resolve_safe_path` centralizadas en `core/context/metadata_paths.py`. No hay regex duplicados.
- **ContextLoader migrado**: Sustituida lógica manual por `MetadataPaths.metadata_root()`.
- **Adapter migrado**: `_normalize_request` y `_load_task_contract` ahora usan `MetadataPaths` y los validadores expuestos.
- **AutonomousRunner migrado**: Lógica de resolución de metadatos en `_materialize_task_artifacts` migrada, preservando el fallback histórico hacia `.harness-internal`.
- **Allowed-path validator migrado**: Ahora utiliza el `resolve_safe_path` centralizado.

## Resultados de Verificación
- **Tests**: 543 passed, 4 skipped.
- **Ruff**: Passed (clean).
- **Diagnostics**: READY.
- **Task Contract Validator**: Válido (exit 0).
- **Revisión READ-ONLY del diff**: Exitosa, las modificaciones respetan el scope de solo resolver metadatos sin alterar lógica funcional del runner o workspace.
- **Cero cambios físicos de metadata**: Los archivos `memory`, `tasks`, etc. no se movieron en esta fase, cumpliendo con la regla fundamental.
- **HARNESS-0022**: No ejecutado.
