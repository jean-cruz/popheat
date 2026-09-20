---
phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry
plan: 02
subsystem: infra
tags: [iris, iop, pyprod, python, tdd, batching, telemetry, heat-classification]

requires:
  - phase: 02-01
    provides: "PopHeat.Production tracer (CatalogPollingService -> ScoreClassifyProcess -> PersistOperation) running one venue per poll, real popularity/heat-classification math, PopHeat.Reading + PopHeat.BatchTelemetry persistent classes"
provides:
  - "popheat_pipeline/scoring.py: pure, IRIS-independent module with select_batch (circular/modulo batching), load_thresholds (config-driven with safe defaults), compute_popularity, classify_heat (thresholds-as-parameter), compute_throughput (zero-safe)"
  - "config/heat_thresholds.json: editable nightlife/daytime CRITICO/ALTO/MEDIO thresholds (HEAT-03)"
  - "components.py: CatalogPollingService cycles the full 906-venue catalog in 150-venue/3s batches with correct wrap-around; ScoreClassifyProcess/PersistOperation have per-batch failure isolation and a scoped, non-blocking telemetry insert"
  - "PopHeat.BatchTelemetry.RecentBatches(): TOP-20, newest-first %SQLQuery (TELE-05)"
affects: [03]

actuals:
  tokens: 9400
  tasks: 2
  commits: 4
plan_head_before: 27087cf6a1a5eb0930e4dd7394faa5f8a6707304

tech-stack:
  added: []
  patterns:
    - "Pure-math extraction: all IRIS-independent business logic (popularity/classification/batching/throughput) lives in a plain python3-importable module (scoring.py); iop-dependent glue in components.py only wires it to the production"
    - "Whole-batch-scope try/except for failure isolation: the try/except boundary matches the unit-of-work (one batch), never a single item inside it, so a broken batch is isolated without poisoning the process for the next scheduled tick"
    - "Two disjoint try/except blocks for 'never let X block Y': the telemetry insert's try/except scopes ONLY the telemetry call, physically separate in the source from the Reading-insert loop's try/except, so a reviewer can see the isolation by inspection, not just trust a comment"

key-files:
  created:
    - popheat_pipeline/scoring.py
    - config/heat_thresholds.json
    - tests/test_scoring.py
  modified:
    - popheat_pipeline/components.py
    - iris/PopHeat/BatchTelemetry.cls

key-decisions:
  - "gsd_run check tdd-red-evidence's TAP parser (parseNodeTestSummary/tapFailedTestNames) targets Node's test-runner TAP output and does not parse Python's `unittest -v` text output -- feeding it produced `zero_tests_discovered` regardless of genuine failures. RED evidence for both tasks was captured manually instead: the actual pre-implementation `unittest -v` output is quoted in each RED commit message and reproduced below, showing real failures/errors targeting exactly the new behavior each task adds."
  - "Docker was present in this execution sandbox but its daemon socket was not accessible (`permission denied` on `/var/run/docker.sock`), so the plan's live `docker compose exec` trial for Task 2's batch-failure-isolation/telemetry-non-blocking behavior could not be run. Per the dispatch's explicit fallback instruction, these behaviors were instead exercised via a stubbed-instantiation trial: `iris-pex-embedded-python` + `tzdata` (already contest-approved in Plan 02-01) were pip-installed locally so `import iop` is the REAL framework (not a hand-rolled fake of it); only the `iris` embedded-SQL/object-persistence bridge (which genuinely cannot exist outside a running IRIS process) was stubbed. All 4 targeted behaviors passed; the full script is reproduced below."
  - "Task 1's precondition ('PopHeat.Production is running') could not be checked live for the same Docker-access reason. Since Task 1's actual deliverable (scoring.py + components.py edits) and its own <verify> command are pure-Python and do not require a running IRIS instance, work proceeded via code review + unit tests rather than halting on an unreachable precondition -- consistent with the same documented fallback allowance."
  - "Fixed a self-inflicted test bug during Task 1's RED phase: test_missing_required_key_defaults_to_baixo originally used popularity=0.99 against a thresholds dict missing ALTO/MEDIO/daytime, but 0.99 matches CRITICO on the very first comparison, so the missing-key code path was never exercised and the test failed for the WRONG reason. Fixed by lowering to 0.30, which forces evaluation to fall through to the missing ALTO key before GREEN was implemented."

requirements-completed: [INGE-02, INGE-03, INGE-04, INGE-05, HEAT-03, HEAT-04, TELE-03, TELE-04, TELE-05]

coverage:
  - id: D1
    description: "select_batch selects a full 150-venue batch from the catalog via circular (modulo) indexing, including a genuine mid-batch wrap at the catalog boundary and a short-catalog (length < size) true circular repeat, and never crashes on an empty catalog"
    requirement: [INGE-02, INGE-03]
    verification:
      - kind: unit
        ref: "tests/test_scoring.py#SelectBatchTests (test_basic_batch_no_wrap, test_wrap_boundary_mid_batch, test_two_calls_in_a_row_wrap_correctly, test_short_catalog_repeats_items_true_circular_wrap, test_empty_catalog_returns_empty_batch_no_crash, test_full_cycle_revisits_every_venue)"
        status: pass
    human_judgment: false
  - id: D2
    description: "CatalogPollingService maintains an in-memory circular cursor (initialized in on_init, never __init__) and sends the WHOLE 150-venue batch as one CatalogBatch message per poll; an empty catalog logs and returns without sending"
    requirement: [INGE-02, INGE-03, INGE-04]
    verification:
      - kind: manual_procedural
        ref: "code review of popheat_pipeline/components.py CatalogPollingService.on_init/on_poll; no live IRIS run possible in this sandbox (Docker daemon socket inaccessible)"
        status: pass
    human_judgment: true
    rationale: "Requires a running IoP production/timer adapter to observe live; not independently unit-testable without the iop runtime. Verified by code review against the plan's exact behavior spec; not exercised end-to-end against a live IRIS container in this sandbox."
  - id: D3
    description: "load_thresholds returns the spec-default thresholds on missing file, malformed JSON, out-of-range value, or missing required key, and returns the file's own values when valid -- classify_heat accepts thresholds as a parameter (not a module constant) and defaults to BAIXO on any lookup failure"
    requirement: [HEAT-03, HEAT-04]
    verification:
      - kind: unit
        ref: "tests/test_scoring.py#LoadThresholdsTests (all 5 cases), #ClassifyHeatTests (test_missing_required_key_defaults_to_baixo, test_empty_thresholds_defaults_to_baixo, test_returns_all_four_labels, test_daytime_category_uses_daytime_scale)"
        status: pass
    human_judgment: false
  - id: D4
    description: "ScoreClassifyProcess loads thresholds fresh (load_thresholds call, no caching) at the start of every on_message call"
    requirement: [HEAT-03]
    verification:
      - kind: manual_procedural
        ref: "code review of popheat_pipeline/components.py ScoreClassifyProcess.on_message -- load_thresholds(str(HEAT_THRESHOLDS_PATH)) is the first statement inside the try block, called on every invocation, never stored on self"
        status: pass
    human_judgment: true
    rationale: "Freshness-per-call is a structural property of the code (no caching variable exists), verified by inspection; a live multi-tick trial to observe a config edit taking effect was not possible without Docker access."
  - id: D5
    description: "compute_throughput returns count/elapsed_seconds when elapsed>0, and exactly 0 (never divide-by-zero, never None) when elapsed<=0, including the (0,0) case"
    requirement: [TELE-03]
    verification:
      - kind: unit
        ref: "tests/test_scoring.py#ComputeThroughputTests (test_normal_division, test_zero_elapsed_returns_zero, test_negative_elapsed_returns_zero, test_zero_count_and_zero_elapsed_returns_zero, test_return_type_is_int_zero_not_float_or_none)"
        status: pass
    human_judgment: false
  - id: D6
    description: "A forced exception in ScoreClassifyProcess's per-batch scoring loop is caught, logged via log_error, and produces no send_request_sync call (no ScoredBatch reaches PersistOperation) -- while a subsequent call on the SAME process instance with good data still succeeds, proving the failure was isolated to one batch"
    requirement: [INGE-05]
    verification:
      - kind: integration
        ref: "live-stubbed trial (scratchpad/verify_task2_live.py, reproduced below): TestableScoreClassifyProcess with a monkeypatched compute_popularity raising RuntimeError for one call"
        status: pass
    human_judgment: true
    rationale: "Not unit-testable in scoring.py alone (the isolation logic lives in ScoreClassifyProcess, which subclasses iop.BusinessProcess). Exercised via a live-stubbed instantiation using the REAL iop package (pip-installed) rather than a docker compose exec trial, per the sandbox's Docker-access limitation; a human should confirm this also holds in a live docker compose exec trial when Docker access is available."
  - id: D7
    description: "PersistOperation's Reading-insert loop and BatchTelemetry insert are in two textually-disjoint try/except blocks: a mid-batch Reading failure logs and returns without ever attempting telemetry; a telemetry-only failure logs and is swallowed without touching/rolling back Reading rows already saved"
    requirement: [INGE-04, TELE-04]
    verification:
      - kind: integration
        ref: "live-stubbed trial (scratchpad/verify_task2_live.py, reproduced below): FakeIris simulating (a) telemetry-save failure after 2 successful Reading saves, (b) Reading-save failure on the 2nd of 2 readings"
        status: pass
      - kind: manual_procedural
        ref: "components.py lines 236-254 (Reading try/except) vs 260-269 (BatchTelemetry try/except) -- textually disjoint line ranges confirmed by direct inspection (grep -n)"
        status: pass
    human_judgment: true
    rationale: "Same as D6 -- exercised via live-stubbed instantiation of the real iop-based PersistOperation with a fake `iris` module rather than a live docker compose exec trial; recommend a human confirm against the real container when Docker access is restored."
  - id: D8
    description: "PopHeat.BatchTelemetry.RecentBatches() is a %SQLQuery returning at most the 20 most-recently-recorded batches, ordered newest-first"
    requirement: [TELE-05]
    verification:
      - kind: manual_procedural
        ref: "grep -n 'TOP 20' iris/PopHeat/BatchTelemetry.cls; class-definition syntax reviewed against IRIS %SQLQuery conventions and Plan 02-01's existing Reading.cls/BatchTelemetry.cls style"
        status: pass
    human_judgment: true
    rationale: "Requires `$SYSTEM.OBJ.LoadDir` compilation against a running IRIS instance to prove it actually compiles and returns correct rows -- not possible in this sandbox (Docker daemon inaccessible). Query syntax follows standard IRIS %SQLQuery class-query conventions; a human should run the plan's own recompile step (docker/init-production.sh's $SYSTEM.OBJ.LoadDir) and query RecentBatches() live before considering this fully proven."

duration: ~90 min
completed: 2026-09-20
status: complete
---

# Phase 2 Plan 2: Real Batching, Full-Catalog Cycling, Failure Isolation & Hardened Telemetry Summary

**Extracted the popularity/classification/batching/telemetry math into a standalone, IRIS-independent `scoring.py` with 24 passing unit tests; the production now cycles the full 906-venue catalog in real 150-venue/3-second batches with correct wrap-around, isolates whole-batch failures without stopping the next scheduled tick, re-reads heat thresholds from config every cycle, and persists telemetry in a way that can never be blocked or rolled back by a telemetry-only failure.**

## Performance

- **Duration:** ~90 min
- **Tasks:** 2 (both `tdd="true"`, each executed as a genuine RED -> GREEN cycle)
- **Files created:** 3 (`scoring.py`, `config/heat_thresholds.json`, `tests/test_scoring.py`)
- **Files modified:** 2 (`components.py`, `BatchTelemetry.cls`)

## Accomplishments

- `popheat_pipeline/scoring.py`: a plain, `iop`/`iris`-free module (verified via an `ast`-based import check) holding `select_batch` (circular/modulo batching with true mid-batch wrap and an empty-catalog guard), `load_thresholds` (config-driven with a validated fallback to spec defaults), `compute_popularity`/`classify_heat` (moved unchanged from the tracer, `classify_heat` now takes `thresholds` as a parameter), and `compute_throughput` (zero-safe division) -- 24/24 unit tests pass
- `config/heat_thresholds.json`: the flat, editable nightlife/daytime CRITICO/ALTO/MEDIO defaults, mirroring `config/catalog_build.json`'s style
- `CatalogPollingService` now walks the full catalog via an in-memory circular cursor (`on_init`, not `__init__`), sending one whole 150-venue `CatalogBatch` message per 3-second poll; an empty catalog is a logged no-op, not a crash
- `ScoreClassifyProcess` loads thresholds fresh every call (no caching) and wraps the entire per-batch scoring loop in one try/except: a forced failure is logged and produces no downstream message, while the next poll tick and even the next call on the SAME process instance are unaffected
- `PersistOperation` splits the Reading-insert loop and the BatchTelemetry insert into two textually-disjoint try/except blocks, so a telemetry-only failure can never touch already-saved Reading rows, and a mid-batch Reading failure never reaches the telemetry insert at all
- `PopHeat.BatchTelemetry.RecentBatches()`: a `TOP 20 ... ORDER BY RecordedAt DESC` `%SQLQuery` for TELE-05's recent-history view

## Task Commits

Each task followed a genuine RED -> GREEN TDD cycle (no REFACTOR commit was needed -- the GREEN implementation was already clean):

1. **Task 1: Real 150/3s batching, full-catalog wrap-around cycling, config-driven thresholds**
   - RED: `1a1117a` (test) -- `tests/test_scoring.py` + naive/incomplete `select_batch`/`load_thresholds` stubs; confirmed 8 failures + 2 errors targeting the new behavior
   - GREEN: `eb29a9f` (feat) -- full `select_batch`/`load_thresholds` implementation, `classify_heat` signature change, `components.py` wired to import from `scoring.py` and use the circular cursor + fresh thresholds; 19/19 tests pass
2. **Task 2: Per-batch failure isolation and hardened, non-blocking, recent-20 telemetry**
   - RED: `5ec8265` (test) -- `ComputeThroughputTests` added against a naive `count/elapsed_seconds` stub; confirmed 1 failure + 3 errors
   - GREEN: `56e56a8` (feat) -- `compute_throughput` implemented, `ScoreClassifyProcess`/`PersistOperation` failure-isolation/telemetry-split added, `RecentBatches()` query added; 24/24 tests pass, plus a live-stubbed integration trial (see below)

**Plan metadata:** pending (this SUMMARY.md commit)

## Files Created/Modified

- `popheat_pipeline/scoring.py` -- pure math/batching/telemetry module (new)
- `config/heat_thresholds.json` -- editable heat-level thresholds (new)
- `tests/test_scoring.py` -- 24 unit tests covering every function in `scoring.py` (new)
- `popheat_pipeline/components.py` -- `CatalogPollingService` circular cursor + batching; `ScoreClassifyProcess`/`PersistOperation` failure isolation + telemetry split; imports from `scoring.py` (modified)
- `iris/PopHeat/BatchTelemetry.cls` -- `RecentBatches()` query added (modified)

## Decisions Made

See frontmatter `key-decisions`. In short: the `gsd_run check tdd-red-evidence` tool's TAP parser doesn't understand Python `unittest` output (documented, RED evidence captured manually instead); Docker's daemon socket was inaccessible in this sandbox so both the Task 1 precondition check and Task 2's live `docker compose exec` trial were replaced with the plan's own documented fallback (a stubbed-instantiation trial using the REAL, pip-installed `iop` package); and one self-inflicted test bug in Task 1's RED phase (a popularity value that accidentally matched the wrong threshold tier) was found and fixed before GREEN.

## RED Evidence (manually captured)

### Task 1 RED (commit `1a1117a`)

```
$ python3 -m unittest tests.test_scoring -v
...
FAILED (failures=8, errors=2)
```
8 failures + 2 errors, all in `SelectBatchTests`/`LoadThresholdsTests`/`ClassifyHeatTests`, targeting exactly the naive/incomplete `select_batch` (no modulo wrap, no empty guard) and `load_thresholds` (no fallback) stubs. Full traceback captured at commit time; representative failures:
- `test_wrap_boundary_mid_batch`: `AssertionError: 6 != 150` (no wrap-around)
- `test_empty_catalog_returns_empty_batch_no_crash`: `AssertionError: 150 != 0` (wrong next_cursor)
- `test_missing_file_returns_defaults`: `FileNotFoundError` (no fallback)
- `test_out_of_range_value_returns_defaults`: `AssertionError` (no validation)

### Task 2 RED (commit `5ec8265`)

```
$ python3 -m unittest tests.test_scoring -v
...
FAILED (failures=1, errors=3)
```
1 failure + 3 errors, all in `ComputeThroughputTests`:
- `test_zero_elapsed_returns_zero`, `test_zero_count_and_zero_elapsed_returns_zero`, `test_return_type_is_int_zero_not_float_or_none`: `ZeroDivisionError: division by zero`
- `test_negative_elapsed_returns_zero`: `AssertionError: -150.0 != 0`

## Live-Stubbed Integration Trial (Task 2, Docker-access fallback)

Docker is installed in this sandbox but its daemon socket returns `permission denied`, so the plan's live `docker compose exec` trial for INGE-05/INGE-04/TELE-04 could not be run. Per the dispatch's explicit fallback instruction, `iris-pex-embedded-python` + `tzdata` (already package-legitimacy-approved in Plan 02-01) were `pip install`ed locally so `import iop` loads the REAL framework -- not a hand-rolled fake of it. Only the `iris` module itself (the embedded-SQL/object-persistence bridge, which genuinely cannot exist outside a running IRIS process) was stubbed with a minimal fake tracking saved objects and simulating targeted failures.

Script: `verify_task2_live.py` (archived below for reproducibility; not committed to the repo -- it is a verification harness, not a deliverable, and depends on locally-installed `iop`/`iris-pex-embedded-python` that is not a project dependency).

**4/4 checks passed:**
1. A monkeypatched `compute_popularity` raising `RuntimeError` for one `ScoreClassifyProcess.on_message` call is caught, logged via `log_error`, produces `None` (no `send_request_sync` call) -- confirming `PersistOperation` never sees the broken batch.
2. A subsequent call on the SAME process instance with good data succeeds normally -- confirming the failure did not poison process state (INGE-05: this batch is an isolated error, not a process-wide fault).
3. A `PersistOperation.on_message` run where the `BatchTelemetry` save raises: both Reading rows are still present in the fake registry, no exception propagates out of `on_message`, and exactly one `log_error` call is recorded mentioning "telemetry persistence failed" (TELE-04).
4. A `PersistOperation.on_message` run where the 2nd of 2 Reading saves raises: `on_message` returns `None`, the `BatchTelemetry` registry entry is never created (telemetry never attempted after a Reading failure), and exactly one `log_error` call is recorded mentioning "batch persistence failed" (INGE-04).

```
PASS: forced scoring exception isolated -- logged, no send_request_sync call
PASS: subsequent good batch on the SAME instance succeeds (state not poisoned)
PASS: telemetry insert failure logged, readings already saved are untouched, no raise
PASS: mid-batch reading failure isolated, telemetry never attempted, no partial-batch telemetry

ALL LIVE-STUBBED TASK 2 CHECKS PASSED
```

**Recommendation for a human with Docker access:** re-run this same scenario (or the plan's originally-specified live `docker compose exec` trial with a deliberately malformed venue injected into one batch) against the actual running container before the contest demo, to confirm the real IRIS `iris.sql`/object-persistence layer behaves identically to the stub under failure.

<details>
<summary>Full verification script (verify_task2_live.py, not committed -- verification harness only)</summary>

```python
"""Ad-hoc live-stubbed verification of Task 2's failure-isolation and
telemetry-non-blocking behaviors (not part of the committed test suite --
ScoreClassifyProcess/PersistOperation depend on the `iop` runtime, per the
plan's own note that this behavior is exercised via stubbed instantiation
rather than the pure-scoring.py unit tests)."""

import sys
import types

sys.path.insert(0, "/home/jean/git/popheat/.claude/worktrees/agent-a31f3e84fa9e89ac0")

import popheat_pipeline.components as c


class FakeLogHost:
    """Mixin capturing log_error calls and send_request_sync calls without
    touching the real iop runtime dispatch machinery."""

    def __init__(self):
        self.errors = []
        self.sent = []

    def log_error(self, msg, to_console=None):
        self.errors.append(msg)

    def log_info(self, msg, to_console=None):
        pass

    def send_request_sync(self, target, message):
        self.sent.append((target, message))
        return message


# ---------------------------------------------------------------------------
# 1. ScoreClassifyProcess: whole-batch failure isolation (INGE-05)
# ---------------------------------------------------------------------------

class TestableScoreClassifyProcess(FakeLogHost, c.ScoreClassifyProcess):
    def __init__(self):
        FakeLogHost.__init__(self)
        self.Persist = "PersistOperation"


proc = TestableScoreClassifyProcess()

batch_bad = c.CatalogBatch(
    venues=[{"id": "node/1", "name": "Bad Venue", "category": None, "lat": 41.14, "lon": -8.61}],
    batch_started_at="2026-09-20T22:00:00+01:00",
)

# Force a failure: monkeypatch compute_popularity to raise for this call.
original_compute_popularity = c.compute_popularity


def raising_compute_popularity(category, when):
    raise RuntimeError("simulated scoring failure")


c.compute_popularity = raising_compute_popularity
result_bad = proc.on_message(batch_bad)
c.compute_popularity = original_compute_popularity

assert result_bad is None, f"expected None on batch failure, got {result_bad!r}"
assert len(proc.errors) == 1, f"expected exactly 1 log_error call, got {proc.errors!r}"
assert "simulated scoring failure" in proc.errors[0]
assert len(proc.sent) == 0, "PersistOperation must never receive the broken batch"
print("PASS: forced scoring exception isolated -- logged, no send_request_sync call")

# Now prove the SAME process instance is not poisoned: a subsequent call with
# good data (real compute_popularity/classify_heat) must still succeed.
batch_good = c.CatalogBatch(
    venues=[{"id": "node/2", "name": "Good Venue", "category": "bar", "lat": 41.14, "lon": -8.61}],
    batch_started_at="2026-09-20T22:00:03+01:00",
)
result_good = proc.on_message(batch_good)
assert result_good is not None
assert len(proc.sent) == 1
target, message = proc.sent[0]
assert len(message.readings) == 1
assert message.readings[0]["heat_level"] in ("BAIXO", "MEDIO", "ALTO", "CRITICO")
print("PASS: subsequent good batch on the SAME instance succeeds (state not poisoned)")


# ---------------------------------------------------------------------------
# 2. PersistOperation: telemetry failure never blocks/rolls back readings
#    already saved (TELE-04), and a mid-batch reading failure never leaves
#    a partial batch for telemetry to record (INGE-04).
# ---------------------------------------------------------------------------

class FakeStatus:
    def __init__(self, ok):
        self._ok = ok

    def __bool__(self):
        return self._ok


class FakeObject:
    def __init__(self, cls_name, registry, fail_on_save=False):
        self._cls_name = cls_name
        self._registry = registry
        self._fail_on_save = fail_on_save
        self._props = {}

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._props[name] = value

    def _Save(self):
        if self._fail_on_save:
            raise RuntimeError("simulated telemetry save failure")
        self._registry.setdefault(self._cls_name, []).append(dict(self._props))
        return FakeStatus(True)


class FakeClassHandle:
    """Stands in for the object `iris.cls(name)` returns -- real code calls
    `._New()` on it to get a fresh persistable instance."""

    def __init__(self, factory):
        self._factory = factory

    def _New(self):
        return self._factory()


class FakeIris:
    """Fake `iris` module: PopHeat.Reading saves succeed; PopHeat.BatchTelemetry
    save raises -- proves TELE-04 (telemetry failure never blocks/rolls back
    the Reading rows already saved)."""

    def __init__(self, saved_registry, fail_telemetry=False, fail_readings_at=None):
        self.saved = saved_registry
        self.fail_telemetry = fail_telemetry
        self.fail_readings_at = fail_readings_at
        self._reading_count = 0

    def cls(self, name):
        if name == "PopHeat.Reading":
            def factory():
                self._reading_count += 1
                fail = self.fail_readings_at is not None and self._reading_count == self.fail_readings_at
                return FakeObject(name, self.saved, fail_on_save=fail)
            return FakeClassHandle(factory)
        if name == "PopHeat.BatchTelemetry":
            return FakeClassHandle(lambda: FakeObject(name, self.saved, fail_on_save=self.fail_telemetry))
        raise AssertionError(f"unexpected class {name}")


class FakeIrisModule(types.ModuleType):
    def __init__(self, fake_iris):
        super().__init__("iris")
        self._fake_iris = fake_iris

    def cls(self, name):
        return self._fake_iris.cls(name)


class TestablePersistOperation(FakeLogHost, c.PersistOperation):
    def __init__(self):
        FakeLogHost.__init__(self)


readings = [
    {
        "venue_id": "node/1",
        "name": "Venue One",
        "category": "bar",
        "lat": 41.14,
        "lon": -8.61,
        "popularity": 0.5,
        "heat_level": "ALTO",
        "observed_at": "2026-09-20T22:00:00+01:00",
    },
    {
        "venue_id": "node/2",
        "name": "Venue Two",
        "category": "cafe",
        "lat": 41.15,
        "lon": -8.62,
        "popularity": 0.3,
        "heat_level": "MEDIO",
        "observed_at": "2026-09-20T22:00:00+01:00",
    },
]

# --- Case A: telemetry insert fails, readings must still be persisted ---
saved_a = {}
fake_iris_a = FakeIris(saved_a, fail_telemetry=True)
sys.modules["iris"] = FakeIrisModule(fake_iris_a)

op_a = TestablePersistOperation()
scored_batch = c.ScoredBatch(readings=readings, batch_started_at="2026-09-20T22:00:00+01:00")
result_a = op_a.on_message(scored_batch)

assert len(saved_a.get("PopHeat.Reading", [])) == 2, "both readings must be saved despite telemetry failure"
assert "PopHeat.BatchTelemetry" not in saved_a, "telemetry save raised -- must not appear in registry"
assert len(op_a.errors) == 1 and "telemetry persistence failed" in op_a.errors[0]
assert result_a is not None, "on_message must not raise/propagate the telemetry failure"
print("PASS: telemetry insert failure logged, readings already saved are untouched, no raise")

# --- Case B: mid-batch reading failure must not leave a partial batch for
#     telemetry, and telemetry must never be attempted ---
saved_b = {}
fake_iris_b = FakeIris(saved_b, fail_telemetry=False, fail_readings_at=2)
sys.modules["iris"] = FakeIrisModule(fake_iris_b)

op_b = TestablePersistOperation()
result_b = op_b.on_message(scored_batch)

assert result_b is None, "a mid-batch reading failure must return None (no request returned)"
assert "PopHeat.BatchTelemetry" not in saved_b, "telemetry must never be attempted after a reading failure"
assert len(op_b.errors) == 1 and "batch persistence failed" in op_b.errors[0]
print("PASS: mid-batch reading failure isolated, telemetry never attempted, no partial-batch telemetry")

print("\nALL LIVE-STUBBED TASK 2 CHECKS PASSED")
```

</details>

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a test that wasn't exercising the behavior it claimed to (Task 1 RED phase)**
- **Found during:** Task 1, initial RED run
- **Issue:** `test_missing_required_key_defaults_to_baixo` used `classify_heat("bar", 0.99, {"nightlife": {"CRITICO": 0.60}})` expecting `"BAIXO"`, but `0.99 >= 0.60` matches CRITICO on the very first threshold check -- the missing `ALTO`/`MEDIO` keys are never consulted, so the test would have passed even against a completely broken thresholds dict for the wrong reason.
- **Fix:** Lowered the popularity to `0.30` (below CRITICO), forcing the evaluation loop to fall through to the missing `ALTO` key and exercise the intended `KeyError` -> `BAIXO` fallback path.
- **Files modified:** `tests/test_scoring.py`
- **Verification:** With the corrected `popularity=0.30`, the pre-GREEN RED run showed `AssertionError: 'CRITICO' != 'BAIXO'` for the ORIGINAL `popularity=0.99` version of this test (proving it was a real gap at that stage); after lowering to `0.30` the test genuinely exercises the missing-`ALTO`-key fallback and passes once the `try/except`-wrapped `classify_heat` (already correct at that point in Task 1's flow) runs.
- **Committed in:** `eb29a9f` (part of the GREEN commit, since the bug was caught and fixed before GREEN was finalized)

**2. [Rule 3 - Blocking] `gsd_run check tdd-red-evidence`'s TAP parser does not parse Python `unittest` output**
- **Found during:** Task 1, attempting to persist RED evidence per the canonical TDD reference
- **Issue:** The tool's classifier (`parseNodeTestSummary`/`tapFailedTestNames`) is built for Node's TAP-format test runner output. Feeding it a `python3 -m unittest -v` transcript (even with `exitCode`/`command`/`targetTest` populated) returns `verdict: INVALID_RED, reason: zero_tests_discovered` regardless of how many real tests failed, because it cannot parse the non-TAP text.
- **Fix:** RED evidence was captured manually instead -- the genuine pre-implementation `unittest -v` output (command, exit code, failure count, and representative tracebacks) is quoted in each RED commit message and reproduced in this SUMMARY's "RED Evidence" section above. This is a tooling gap in a Node-oriented verb applied to a Python project, not a shortcut around the RED requirement itself -- both RED runs genuinely failed for the targeted reasons before any GREEN commit was made.
- **Files modified:** none (documentation-only workaround)
- **Verification:** Both RED runs' failures map 1:1 to the specific new/changed functions each task adds (`select_batch`/`load_thresholds`/`classify_heat` for Task 1, `compute_throughput` for Task 2) -- no unrelated or collection-level failures.
- **Committed in:** N/A (documented here and in commit messages)

**3. [Rule 3 - Blocking] Docker daemon inaccessible in this execution sandbox**
- **Found during:** Task 1's precondition check and Task 2's live-trial requirement
- **Issue:** `docker compose exec -T iris iop --status` and any `docker compose up -d` fail with `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock` -- Docker CLI/daemon binaries are present but the socket is not accessible from this sandboxed execution context.
- **Fix:** Per the dispatch's explicit fallback instruction, proceeded without live IRIS verification: Task 1's precondition doesn't block code-only work whose own `<verify>` is pure Python; Task 2's live trial was replaced with a stubbed-instantiation trial using the real, pip-installed `iop` package (see "Live-Stubbed Integration Trial" above).
- **Files modified:** none (verification-strategy workaround only)
- **Verification:** All plan-level `<verification>` items that don't require a live IRIS instance were run and pass (unit tests, static checks); items 2 and 3 of the plan's `<verification>` section (a live multi-tick production run, and `$SYSTEM.OBJ.LoadDir` compilation of the updated `BatchTelemetry.cls`) remain unverified against the real container and are flagged under "Next Phase Readiness" below.
- **Committed in:** N/A (environment limitation, not a code change)

---

**Total deviations:** 3 (1 auto-fixed bug in a self-authored test, 2 documented tooling/environment limitations with fallback verification strategies applied)
**Impact on plan:** None of these affect the shipped code's correctness -- all pure-Python logic is proven by 24 passing unit tests, and the iop-dependent failure-isolation/telemetry-split logic is proven by a live-stubbed trial against the REAL `iop` framework. The only open item is confirming the same behavior against an actual running IRIS container, which requires Docker access this sandbox does not have.

## Issues Encountered

- **Docker daemon inaccessible (environment-specific, not a code issue):** `docker ps` and `docker compose` commands fail with a socket permission error in this execution sandbox, even though the Docker CLI itself is installed. This blocked live verification of Task 1's precondition and Task 2's live trial. Worked around per the dispatch's documented fallback (see Deviations #3 above); flagging for the next session/human with Docker access to run the live verification before the contest demo.
- **`gsd_run check tdd-red-evidence` doesn't support Python test output (tooling gap, not a code issue):** documented above; does not affect the genuineness of the RED->GREEN cycles performed, only the automated-tool-verifiable-ness of that evidence.

## User Setup Required

None -- no external service configuration required. Same as Plan 02-01: `data/venues.json` must be present at the repo root (it already is, from Phase 1).

## Next Phase Readiness

- All pure-Python scoring/batching/telemetry logic is implemented and unit-tested (24/24 passing); `components.py` is updated to use it and passes `py_compile` + a full real `import` (with `iris-pex-embedded-python` installed) with no errors.
- **Before the contest demo, a human with Docker access should:**
  1. Run `docker compose up -d` (or `docker compose restart iris` if already running) and confirm `docker compose exec -T iris iop --status` shows `PopHeat.Production` running.
  2. Recompile `iris/PopHeat/BatchTelemetry.cls` (re-run the `$SYSTEM.OBJ.LoadDir` step from `docker/init-production.sh`, or an equivalent one-off `docker compose exec` call) so the new `RecentBatches()` query is live, then confirm it returns <=20 rows newest-first via `docker compose exec -T iris iris sql POPHEAT <<< "SELECT * FROM PopHeat_BatchTelemetry.RecentBatches()"` (or the SQL-projected table equivalent).
  3. Watch the production run for at least two full 3-second poll ticks and confirm two distinct 150-venue batches are persisted (906 venues means the cursor should NOT repeat the same 150 across consecutive ticks until the full cycle completes).
  4. Optionally inject a deliberately malformed venue (e.g., edit `data/venues.json` temporarily to include a venue with a non-serializable or wildly invalid field) into one batch and confirm the IRIS Event Log shows a `batch failed` / `batch persistence failed` error for that tick without stopping the next scheduled tick.
- Plan 02-02 fully satisfies its `requirements-completed` list (INGE-02 through INGE-05, HEAT-03/HEAT-04, TELE-03 through TELE-05) at the code + unit-test level; live end-to-end confirmation against the running container is the one remaining gap, tracked above.
- No architectural blockers for Phase 3 (dashboard/API): `PopHeat.Reading` and `PopHeat.BatchTelemetry` schemas are unchanged from Plan 02-01, so Phase 3's read-side work can proceed independent of this plan's live-verification gap.

## Self-Check: PASSED

- All 3 created files verified present on disk (`popheat_pipeline/scoring.py`, `config/heat_thresholds.json`, `tests/test_scoring.py`).
- Commits `1a1117a`, `eb29a9f`, `5ec8265`, `56e56a8` verified present in `git log --oneline --all`.
- Plan-level `<verification>` item 1 re-run: `python3 -m unittest tests.test_scoring -v` -> `OK` (24 tests, 0 failures, 0 errors).
- Plan-level `<verification>` items 2 and 3 (live production run, live `$SYSTEM.OBJ.LoadDir` compile) NOT re-run -- Docker daemon inaccessible in this sandbox; see "Next Phase Readiness" for the human follow-up.
- Acceptance-criteria re-run: `ast`-based no-`iop`/`iris`-import check on `scoring.py` exits 0; `config/heat_thresholds.json` parses with exactly `nightlife`/`daytime` keys each holding numeric `CRITICO`/`ALTO`/`MEDIO`; `grep -n "TOP 20" iris/PopHeat/BatchTelemetry.cls` finds the query; `components.py` lines 236-254 (Reading try/except) and 260-269 (BatchTelemetry try/except) confirmed textually disjoint by direct inspection; no `UPDATE`/`DELETE` statement anywhere in `components.py`.

---
*Phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry*
*Completed: 2026-09-20*
