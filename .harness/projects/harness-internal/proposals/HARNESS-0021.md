# HARNESS-0021 — Native Antigravity CLI Execution Bridge (Sandboxed)

## Problem Statement
El motor `AutonomousRunner` requiere ejecutar de forma física la delegación hacia Antigravity usando el CLI `agy`. Al proveer a la IA del flag `--dangerously-skip-permissions`, existe el riesgo crítico de que el host realice mutaciones destructivas o fuera de scope *antes* de que el post-dispatch check pueda actuar. Se requiere una arquitectura de Sandboxing y Worktrees temporales para mitigar esto de raíz.

## Architecture: Aislamiento por Sandbox

### 1. Planning Execution (Staging Sandbox)
- **Contexto:** Workflow `plan-task`, ejecutado por `orchestrator`, antes de que exista un contrato aprobado.
- **Aislamiento:** El `AutonomousRunner` crea un directorio temporal vacío o restringido (Staging Sandbox). `agy` se ejecuta inyectándole el CWD de este staging.
- **Generación:** La IA escribe su propuesta de Task Contract en este staging.
- **Validación y Aplicación:** El Python Harness lee el YAML generado en el staging. Valida que cumpla el schema oficial, y que los campos estructurales (`task_id`, `workflow`, `specialist`, `scope`) sean coherentes. Solamente si es válido, el **Harness** (no `agy`) mueve/copia el artefacto oficial a `projects/.harness-internal/tasks/` y realiza el commit.

### 2. Implementation Execution (Git Worktree Sandbox)
- **Contexto:** Workflow `implement-task`, ejecutado por especialistas tras `approval_status == approved`.
- **Pre-dispatch Guard:** El Harness recarga el contrato de disco, valida schema, status, matrix de autoridad, scope exacto y verifica que el `HEAD` sea compatible con el `implementation_baseline`.
- **Aislamiento:** El Harness crea un Git Worktree temporal (`git worktree add <temp_dir>`). `agy` es invocado usando el worktree como su `--add-dir` (CWD).
- **Ejecución Mutacional:** La IA modifica el worktree utilizando tools.
- **Post-dispatch Validation (Sandbox):** El Harness ejecuta un análisis de estado sobre el worktree (`git status --porcelain` o `git diff` contra HEAD original).
  - Determina la lista exacta de archivos creados, modificados o eliminados.
  - Verifica que cada uno exista estrictamente dentro de `scope.planned_paths.modify`.
  - Verifica que no hayan commits locales sorpresivos, nuevos tags, ni alteraciones de permisos no autorizadas.
- **Aplicación Controlada (Patching):** Si la validación es 100% exitosa, el Harness procede a importar los cambios al repositorio oficial. La técnica consistirá en trasladar únicamente los archivos autorizados y modificados desde el worktree hacia el repositorio principal de manera selectiva (o mediante un parche controlado `git diff > patch && git apply` restringido al scope).
- **Fallback:** Si hay cualquier violación de scope, el worktree se desecha inmediatamente (garbage collection), no se altera el repositorio principal y el workflow escala a `paused` (requiere humano).

## Audit Trail Semantics (Actualizadas)
Se introducen nuevos estados trazables para reflejar la cadena de custodia de la ejecución aislada:
- `planned`: Harness generó un plan teórico.
- `sandbox_created`: Directorio staging o Git worktree inicializado con éxito.
- `dispatched`: `agy` subprocess lanzado físicamente apuntando al sandbox.
- `executed`: `agy` finalizó con returncode 0, JSON válido y SUCCESS en el sandbox. (NO implica aplicación).
- `validated`: Harness inspeccionó los resultados/diff del sandbox y certifica que cumplen el scope y reglas.
- `applied`: Harness transfirió los cambios validados al working tree oficial.
- `paused`: Violación detectada en validación, u otra detención de gobierno.
- `failed`: Error técnico o de infraestructura (timeout, crash, JSON inválido).
- `completed`: El workflow final comprobó todos los resultados.

## Executor y CLI
El array seguro del subproceso mantendrá:
`["agy", "--print", final_prompt, "--output-format", "json", "--print-timeout", "10m", "--dangerously-skip-permissions", "--add-dir", sandbox_dir]`

## Testing Strategy
1. **Unit Tests:** `tests/test_cli_executor.py` y `tests/test_sandbox.py` mockearán la creación de worktrees y la extracción de diffs.
2. **E2E Test (Opt-In aislada):** `tests/test_e2e_runner.py` inyectará una intención que requiera crear un archivo.
   - Demostrará que `agy` opera en un sandbox y no en el CWD del test.
   - Probará inyectar un archivo "malicioso" fuera de scope en el sandbox; validará que el status cambie a `paused` y que el repositorio final rechace la mutación.
   - Probará el camino feliz donde el archivo válido se mueve a `applied` y finalmente se expone en el workspace de test, deteniéndose correctamente antes de `contador.html`.
