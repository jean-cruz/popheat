# Phase 2: IRIS Ingestion Pipeline — Pattern Map

**Mapped:** 2026-09-20
**Files analyzed:** 7 (new)
**Analogs found:** 2 / 7 (rest are greenfield — no IRIS/Docker code exists yet)

## Context

Phase 1 left exactly two prior-code artifacts: `scripts/build_catalog.py` (stdlib-only CLI, config-driven, atomic-write) and `config/catalog_build.json` (flat JSON config). No IRIS, Docker, or PyProd code exists anywhere in the repo. Most Phase 2 files are therefore genuinely greenfield; the two config/style analogs below are strong and should be followed closely. IRIS-specific structural conventions (Persistent class syntax, PyProd BS/BP/BO wiring, production XML) have no repo precedent and must come from IRIS/PyProd platform conventions (documented in CONTEXT.md's canonical specs, not from codebase analogs) — flagged explicitly in "No Analog Found" below.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `config/heat_thresholds.json` | config | batch (re-read per cycle) | `config/catalog_build.json` | exact |
| `docker-compose.yml` | config | N/A (infra) | none | no analog |
| `iris/PopHeat/Reading.cls` (Persistent class) | model | CRUD (insert-only) | none | no analog |
| `iris/PopHeat/BatchTelemetry.cls` (Persistent class) | model | CRUD (insert-only) | none | no analog |
| PyProd Business Service (timer-driven catalog reader) | service | batch / event-driven | `scripts/build_catalog.py` (`run()`, config loading) | role-match (style only) |
| PyProd Business Process (score + classify) | service | transform | `scripts/build_catalog.py` (`map_element_to_venue`, pure-function style) | role-match (style only) |
| PyProd Business Operation (persist Reading + BatchTelemetry) | service | CRUD | `scripts/build_catalog.py` (`write_json_atomic`, error-isolation style) | role-match (style only) |

## Pattern Assignments

### `config/heat_thresholds.json` (config, batch)

**Analog:** `config/catalog_build.json` (full file, 13 lines)

**Full pattern to mirror** (`config/catalog_build.json` lines 1-13):
```json
{
  "bounding_box": {
    "south": 41.1390,
    "west": -8.6200,
    "north": 41.1510,
    "east": -8.6020
  },
  "amenity_allowlist": ["bar", "pub", "restaurant", "cafe", "fast_food", "nightclub"],
  "overpass_endpoint": "https://overpass-api.de/api/interpreter",
  "request_timeout_seconds": 30,
  "overpass_timeout_seconds": 25,
  "max_response_bytes": 20000000
}
```
Key traits to replicate in `config/heat_thresholds.json`:
- Flat, human-editable JSON — no nesting beyond one level of grouping (mirrors `bounding_box` sub-object for grouped numeric values).
- Every value is a plain number/string/list a developer would hand-tune (no computed or derived fields).
- Committed under `config/`, sibling to `catalog_build.json`, same naming convention (`<subject>_<noun>.json`, snake_case, no version suffix).

**Load + validate pattern to mirror** (`scripts/build_catalog.py` lines 51-114, `ConfigError` + `load_config`):
```python
class ConfigError(Exception):
    """Raised when the build config file is missing or malformed."""

def load_config(path):
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file at {path} is not valid JSON: {e}") from e
    for key in REQUIRED_CONFIG_KEYS:
        if key not in config:
            raise ConfigError(f"Config file at {path} is missing required key: {key}")
    # ... per-key type/shape validation ...
    return config
```
Apply this same shape for the PyProd threshold loader: define `REQUIRED_CONFIG_KEYS` tuple, raise a dedicated `ConfigError`-style exception with a clear message (never a bare `KeyError`/`TypeError`), validate types explicitly (bool-excluded numeric check via `_is_number`, lines 45-48). Because D-10 requires re-read every batch cycle (no caching), call this loader once per tick inside the Business Process/Operation rather than at `on_init`.

---

### PyProd components (service/model roles) — style guidance only, no structural analog

**Source of style:** `scripts/build_catalog.py` overall structure (imports lines 12-21, module-level path/constant declarations lines 23-42, pure mapping functions lines 163-240, `run()` orchestrator lines 271-333, exit-code/error-surfacing convention).

Patterns to carry into PyProd Python code (`%DispatchGetProperty`/`OnProcessInput` methods etc.):
- **Imports:** stdlib-only where possible, grouped alphabetically, no wildcard imports (lines 12-21).
- **Pure functions over classes for transforms:** score computation and heat-level classification should be free functions taking plain data in, returning plain data out (mirrors `map_element_to_venue`, lines 168-210) — easy to unit test independently of IRIS runtime, consistent with the `tests/test_build_catalog.py` existing test style.
- **Explicit custom exceptions, not bare excepts:** define e.g. `ScoringError`/`ClassificationError` mirroring `ConfigError`/`OverpassFetchError` (lines 51-58) — catch narrowly, wrap, re-raise with context (`raise X(...) from e`).
- **Docstrings state the spec rule being implemented** (e.g. "R4 dedup key precision", "VENU-02"): continue this traceability convention, referencing `ingestion-pipeline.spec`/`popularity-model.spec`/`heat-classification.spec`/`telemetry.spec` requirement IDs (INGE-xx, POPU-xx, HEAT-xx, TELE-xx) in docstrings for each new function.
- **Never silently swallow errors** — per-batch failure isolation (INGE-05) should mirror the `run()` function's pattern of catching a specific exception type, printing/logging a clear message, and returning a controlled failure signal (lines 286-308) rather than letting one venue's failure kill the whole batch.

---

## Shared Patterns

### Config loading & validation
**Source:** `scripts/build_catalog.py` lines 51-114 (`ConfigError`, `load_config`, `_is_number`)
**Apply to:** Any PyProd stage that reads `config/heat_thresholds.json` each cycle (D-10).

### Atomic/defensive I/O discipline
**Source:** `scripts/build_catalog.py` lines 243-268 (`write_json_atomic`)
**Apply to:** Not directly reusable (IRIS Persistent class inserts replace file I/O), but the underlying discipline — never leave partial/corrupt state on failure, isolate failure to the smallest unit (one venue / one batch) — should carry into the Business Operation's insert-per-reading logic per D-07 (insert-only) and INGE-05 (failure isolation).

### Requirement-ID traceability in docstrings
**Source:** Throughout `scripts/build_catalog.py` (e.g. lines 3-9, 118-119, 213-217)
**Apply to:** All new PyProd Python files and IRIS class definitions — reference INGE-xx/POPU-xx/HEAT-xx/TELE-xx and D-xx decision IDs from `02-CONTEXT.md` in docstrings/comments.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `docker-compose.yml` | config | N/A | No Docker/infra config exists anywhere in the repo yet; must follow `intersystems/iris-community` official image documentation directly (D-03), not a codebase analog. |
| `iris/PopHeat/Reading.cls` | model | CRUD (insert-only) | No IRIS Persistent class exists in the repo. Structure (properties, `%Persistent` superclass, SqlStorage) must follow IRIS class-definition conventions per D-06/D-08, not a codebase analog. |
| `iris/PopHeat/BatchTelemetry.cls` | model | CRUD (insert-only) | Same as above — first IRIS Persistent class in the project; no prior analog. |
| PyProd Business Service/Process/Operation class scaffolding (`Ens.BusinessService`/`Ens.BusinessProcessBSL`/`Ens.BusinessOperation` subclasses, production `.cls`/XML wiring) | service | event-driven / timer | No PyProd or Interoperability code exists in the repo; this is the project's first IRIS Interoperability Production. Internal topology is explicitly left to planner discretion per CONTEXT.md "Claude's Discretion" — follow IRIS PyProd platform conventions, not a codebase analog. |

## Metadata

**Analog search scope:** entire repo (excluding `.git/`, `.planning/`, `__pycache__`)
**Files scanned:** `scripts/build_catalog.py`, `config/catalog_build.json`, `tests/test_build_catalog.py` (referenced for test-style convention), `specs/*.spec` (referenced via CONTEXT.md canonical_refs, not for code patterns)
**Pattern extraction date:** 2026-09-20
