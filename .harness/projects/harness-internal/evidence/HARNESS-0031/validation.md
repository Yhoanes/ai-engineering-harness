# HARNESS-0031 Pre-Close Validation

## TASK CONTRACT GOVERNANCE
- legacy arrays siguen soportados;
- explicit object scopes soportados;
- deny_all;
- allow_list;
- unrestricted;
- no "*" mágico;
- no "**" mágico;
- unrestricted solo por declaración explícita.

## SCHEMA
- JSON Schema Draft 7;
- oneOf discriminado;
- const;
- additionalProperties: false;
- allow_list requiere values no vacío;
- deny_all/unrestricted no aceptan values;
- modify legacy conserva minItems: 1;
- read/terminal legacy conservan comportamiento histórico.

## NORMALIZATION
- [] → DENY_ALL cuando el campo opcional/caller lo permite;
- populated legacy array → ALLOW_LIST;
- "*" y "**" permanecen literales ALLOW_LIST;
- explicit unrestricted → UNRESTRICTED;
- duplicates → frozenset;
- malformed objects también fallan en normalizer.

## CONSUMERS
- AutonomousRunner ya no usa set(dict);
- secondary Task Contract scope:
  DENY_ALL / ALLOW_LIST / UNRESTRICTED;
- primary ExecutionRequest AND secondary Task Contract;
- rename/new/old path enforcement existente preservado.

## AUTHORITY
Muy importante:

Task Contract:
puede REPRESENTAR explicit UNRESTRICTED.

Authority Matrix:
todavía NO puede CONCEDER explicit UNRESTRICTED.

Por tanto:
validate_allowed_paths_pre:
UNRESTRICTED → fail closed.

validate_authority:
UNRESTRICTED → fail closed.

Incluso si Matrix contiene:
"*"
"**"
NO se convierten a AccessMode.UNRESTRICTED.

Los globs de Authority Matrix mantienen únicamente su semántica histórica de pattern matching para ALLOW_LIST.

## HARNESS-0030
HARNESS-0030 sigue BLOQUEADO.
0031 resolvió: Task Contract representation.
Pero todavía falta: Authority Matrix representation / authorization.

## RUFF DEVIATION
Scoped Ruff: PASS / EXIT 0.
Global Ruff: FAIL / EXIT 1.

Causa global:
tests/test_antigravity_execution_provider.py
Códigos preexistentes detectados: E501, SIM117
Baseline comparison: mismos errores existen en HEAD/v1.9.0.
Out-of-scope file: UNCHANGED.

## HISTORICAL COMPATIBILITY
historical inspected: 33
baseline-valid: 26
baseline-invalid preexisting: 7
baseline-valid still valid: 26
implicit UNRESTRICTED expansions: 0
