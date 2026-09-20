---
phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry
reviewed: 2026-09-20T21:30:12Z
depth: standard
files_reviewed: 11
files_reviewed_list:
  - config/heat_thresholds.json
  - docker-compose.yml
  - docker/init-production.sh
  - iris/PopHeat/BatchTelemetry.cls
  - iris/PopHeat/Reading.cls
  - iris/merge.cpf
  - popheat_pipeline/__init__.py
  - popheat_pipeline/components.py
  - popheat_pipeline/scoring.py
  - settings.py
  - tests/test_scoring.py
findings:
  critical: 2
  warning: 3
  info: 4
  total: 9
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-20T21:30:12Z
**Depth:** standard
**Files Reviewed:** 11
**Status:** issues_found

## Summary

Reviewed the IRIS Interoperability pipeline (`popheat_pipeline/components.py`, `scoring.py`), its supporting IRIS classes (`Reading.cls`, `BatchTelemetry.cls`), config (`heat_thresholds.json`), production wiring (`settings.py`), and container setup (`docker-compose.yml`, `docker/init-production.sh`, `iris/merge.cpf`).

The pure scoring/classification/batching math in `scoring.py` is careful, well-tested, and matches its specs closely (weekend boost, circular distance, zero-safe throughput, safe threshold fallback). However, two correctness gaps in `components.py` undermine guarantees the code's own docstrings and `specs/ingestion-pipeline.spec` claim are met: (1) `PersistOperation` never wraps its reading-insert loop in an IRIS transaction, so a mid-batch `_Save()` failure leaves already-inserted rows for that batch permanently in `PopHeat.Reading` with no telemetry record — directly contradicting the class's own documented "never leaves a mix of this-batch and next-batch rows" claim; (2) `CatalogPollingService.on_poll` has no exception handling around the catalog file read/parse, unlike the deliberately isolated `ScoreClassifyProcess.on_message`, so a missing/corrupt `data/venues.json` at runtime can propagate an exception out of the poll callback and stop all future batches — the opposite of the "failure isolation" goal the code explicitly designs for one stage later in the same pipeline.

Additional warnings cover config-durability and setup-script robustness; several info-level items note stale/misleading comments and unpinned dependency versions.

## Critical Issues

### CR-01: PersistOperation has no transactional rollback for partial batch failures

**File:** `popheat_pipeline/components.py:236-254`
**Issue:** The reading-insert loop calls `obj._Save()` for each reading and raises `PersistenceError` if any single save fails, which is caught by the surrounding `except Exception` and logged. But nothing wraps the loop in an IRIS transaction (`iris.tstart()` / `iris.trollback()`), so every `PopHeat.Reading` row already saved *before* the failing one remains permanently persisted in the database. The method then returns `None` without ever inserting a `BatchTelemetry` row for this batch (step 2 never runs). This directly contradicts the class's own docstring:

> "if the reading loop raises partway through, this method logs and returns immediately WITHOUT attempting the telemetry insert, so a mid-batch persistence failure never leaves a mix of this-batch and next-batch rows"

In reality it *does* leave a mix: a partial set of rows from the failed batch, indistinguishable from rows of the next successful batch, with no telemetry record ever referencing them (violating `specs/ingestion-pipeline.spec` R3 "A batch of venues is scored, classified, and persisted as one unit" and `specs/telemetry.spec` R1's implicit 1:1 batch-to-telemetry expectation).
**Fix:** Wrap the reading-insert loop in an explicit transaction and roll back on failure:
```python
try:
    start = time.monotonic()
    iris.tstart()
    for reading in request.readings:
        obj = iris.cls("PopHeat.Reading")._New()
        ...
        status = obj._Save()
        if not status:
            raise PersistenceError(f"Failed to save PopHeat.Reading: {status}")
    iris.tcommit()
    elapsed = time.monotonic() - start
except Exception as exc:
    iris.trollback()
    self.log_error(f"batch persistence failed: {exc}")
    return None
```

### CR-02: CatalogPollingService.on_poll has no failure isolation around catalog acquisition

**File:** `popheat_pipeline/components.py:112-129`
**Issue:** `on_poll` opens and JSON-parses `data/venues.json` with no try/except:
```python
def on_poll(self):
    with open(VENUES_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    if not catalog:
        ...
```
If the catalog file is missing, truncated, or otherwise unparsable at the moment a poll fires (e.g. mid-redeploy, concurrent edit, disk issue), `open()`/`json.load()` raise an uncaught exception straight out of the polling callback. `ScoreClassifyProcess.on_message`, immediately downstream in the same pipeline, is explicitly and carefully wrapped in `try/except` for exactly this reason — its own docstring states the wrapping exists so "no exception propagates up to break the adapter timer loop that schedules the NEXT poll tick." `on_poll` has no equivalent protection, so an exception here can silently stop all future batches (the pipeline never polls again), the opposite of `specs/ingestion-pipeline.spec` R4 ("A failure while producing or handling one batch is recorded as an error for that batch; it does not stop the next scheduled batch from being processed").
**Fix:** Wrap the catalog read in a try/except that logs and returns (treats a bad read as a no-op tick, same pattern already used for the empty-catalog case):
```python
def on_poll(self):
    try:
        with open(VENUES_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        self.log_error(f"failed to read catalog at {VENUES_PATH}: {exc}")
        return
    ...
```

## Warnings

### WR-01: load_thresholds does not validate that threshold levels are monotonic

**File:** `popheat_pipeline/scoring.py:113-131`
**Issue:** `_thresholds_valid` checks that every threshold value is a number in `[0, 1]` and that both groups/all three levels are present, but never checks `CRITICO >= ALTO >= MEDIO`. Since `classify_heat` evaluates `_LEVELS_HIGH_TO_LOW` in fixed CRITICO→ALTO→MEDIO order and returns on the first match, a hand-edited `config/heat_thresholds.json` with individually in-range but non-monotonic values (e.g. `CRITICO: 0.1, ALTO: 0.5, MEDIO: 0.3`) would pass validation yet silently misclassify most readings as CRITICO. `specs/heat-classification.spec` R4 explicitly anticipates this file being retuned by a non-engineer ("business analyst") without a code change, making this a realistic misconfiguration path with no safety net.
**Fix:** Add an ordering check to `_thresholds_valid`, e.g.:
```python
if not (group_values["CRITICO"] >= group_values["ALTO"] >= group_values["MEDIO"]):
    return False
```

### WR-02: No durable volume for the POPHEAT database — `docker compose down` destroys all data

**File:** `docker-compose.yml:24-25`, `iris/merge.cpf:10-19`
**Issue:** The CPF merge file deliberately creates the `POPHEAT` database under `/usr/irissys/mgr/popheat`, inside the container's own (non-bind-mounted) filesystem, and `docker-compose.yml` defines no named volume for it. The comments correctly note this survives `docker compose restart`/host reboot (container filesystem is retained), but an operator running the very common `docker compose down` (e.g. to pick up an image update, or by habit) removes the container and permanently destroys every `PopHeat.Reading` and `PopHeat.BatchTelemetry` row with no warning — a real risk for a project whose "Core Value" is a working live demo on the contest deadline day.
**Fix:** Either add a named volume mapped to `/usr/irissys/mgr/popheat` so data survives `down`/`up`, or add an explicit comment/README warning next to the compose file stating `docker compose down` is destructive and only `restart` is safe.

### WR-03: Namespace-existence check in init-production.sh parses session output with a fragile generic-digit regex

**File:** `docker/init-production.sh:24-28`
**Issue:**
```sh
NS_EXISTS=$(iris session "$IRIS_INSTANCE" -U%SYS <<IRISEOF 2>&1 | grep -Eo '[01]' | tail -1
write ##class(Config.Namespaces).Exists("${IRIS_NAMESPACE}"),!
halt
IRISEOF
)
```
This greps the entire (stdout+stderr) session transcript for any standalone `0` or `1` character and takes the last one. Any incidental digit in a login banner, version string, or warning printed after the `write` output (or the absence of the expected digit due to a session error) would be silently mis-parsed as the exists/not-exists result, potentially causing the script to skip creating a genuinely missing namespace, or to attempt (harmlessly, but confusingly) recreating an existing one.
**Fix:** Use a more specific marker, e.g. `write "NS_EXISTS=",##class(Config.Namespaces).Exists(...),!` and grep for the literal `NS_EXISTS=` prefix rather than any bare digit.

## Info

### IN-01: `iop --start` failures are unconditionally swallowed with a possibly-wrong message

**File:** `docker/init-production.sh:65`
**Issue:** `iop --start PopHeat.Production --detach || echo "(already running -- ok on re-run)"` prints the same reassuring message for *any* nonzero exit from `iop --start`, not just the "already running" case, which could mask a genuine startup failure during setup.
**Fix:** Check `iop --status` output explicitly, or capture the failure text and only suppress it when it matches an "already running"/"already started" pattern.

### IN-02: Unpinned dependency versions in the setup script

**File:** `docker/init-production.sh:21`
**Issue:** `pip3 install --quiet iris-pex-embedded-python tzdata` installs unpinned latest versions, so re-running setup at a later date (or on a fresh contest-day container) could pull a different version than what was tested.
**Fix:** Pin versions (e.g. `iris-pex-embedded-python==<tested-version>`) if reproducibility before the deadline matters more than always getting the latest patch.

### IN-03: `_thresholds_valid` docstring claims a usage that doesn't exist in `classify_heat`

**File:** `popheat_pipeline/scoring.py:113-131` (docstring) vs. `162-182` (`classify_heat`)
**Issue:** `_thresholds_valid`'s docstring states it is "Used by both `load_thresholds` ... and `classify_heat` (defensive re-check ...)", but `classify_heat` never calls `_thresholds_valid` — it relies solely on its own `try/except Exception: return "BAIXO"` for defensiveness. The end behavior is equivalent, but the comment misdescribes the actual call graph, which could mislead a future maintainer into thinking a validation call exists where it doesn't.
**Fix:** Update the docstring to remove the `classify_heat` usage claim, or actually call `_thresholds_valid` at the top of `classify_heat` as a fast-fail before the try block, to make the comment accurate.

### IN-04: settings.py docstring is stale relative to the shipped implementation

**File:** `settings.py:1-6`
**Issue:** The module docstring still describes the file as wiring a "tracer graph" with "Batching (150/3s, R1) and full-catalog cycling (R2) ... added on top of this same graph in Plan 02-02" as future work, but Plan 02-02 (150-venue batching, circular cycling, full scoring/classification/telemetry) is already implemented in `popheat_pipeline/components.py`, which this file imports and wires unchanged. The comment reads as pre-Plan-02-02 documentation that was never updated after the real pipeline landed.
**Fix:** Update the docstring to describe the current, complete production graph rather than the original tracer-stage plan.

---

_Reviewed: 2026-09-20T21:30:12Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
