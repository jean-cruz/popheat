---
phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry
plan: 01
subsystem: infra
tags: [iris, docker, iop, pyprod, interoperability, embedded-python]

requires: []
provides:
  - "Docker Compose stack running IRIS Community Edition with a POPHEAT namespace auto-created on first boot"
  - "PopHeat.Production (IoP/iris-pex-embedded-python) auto-starting on every container start/restart, no manual step"
  - "PopHeat.Reading and PopHeat.BatchTelemetry SQL-projected Persistent classes"
  - "Full popularity model (per-category Gaussian curves, midnight wrap, weekend boost, randomness, clamp/round) and heat classification (nightlife vs daytime thresholds)"
  - "One real venue processed end-to-end every ~3s: polled -> scored -> classified -> persisted as a Reading row + a BatchTelemetry row"
affects: [02-02]

actuals:
  tokens: 5030
  tasks: 2
  commits: 1
plan_head_before: 7d769de273281367bb0825548b7aff1b2f3337e3

tech-stack:
  added: [iris-pex-embedded-python (iop), tzdata, intersystemsdc/iris-community docker image]
  patterns:
    - "IoP service -> process -> operation topology (CatalogPollingService -> ScoreClassifyProcess -> PersistOperation)"
    - "target() descriptors given an explicit default target name rather than a bare target() -- required workaround, see Deviations"
    - "Embedded-Python object-persistence API (iris.cls(...)._New()/._Save()) used instead of iris.sql.exec for inserts -- required workaround, see Deviations"

key-files:
  created:
    - docker-compose.yml
    - iris/merge.cpf
    - docker/init-production.sh
    - iris/PopHeat/Reading.cls
    - iris/PopHeat/BatchTelemetry.cls
    - popheat_pipeline/__init__.py
    - popheat_pipeline/components.py
    - settings.py
  modified: []

key-decisions:
  - "Task 1 checkpoint (package legitimacy for iris-pex-embedded-python + tzdata) was human-approved in a prior run of this plan before any commits existed; re-recorded here as resolved without re-prompting, per explicit dispatch instruction."
  - "CPF merge file creates the POPHEAT database+namespace via an [Actions] section (CreateDatabase/CreateNamespace), not raw [Databases]/[Namespaces] sections -- verified live against the running container's own entrypoint log, which explicitly names an [Actions] processing phase; the plan's originally-suggested raw-section syntax registers a namespace config entry but never creates the underlying database, leaving the namespace unusable (<DIRECTORY> error on zn)."
  - "POPHEAT database directory is /usr/irissys/mgr/popheat (not /durable/POPHEAT) because CreateDatabase can create one new leaf directory but not multiple missing parent levels; /durable does not pre-exist in the image and CreateDatabase failed with 'Cannot create directory' when pointed there."
  - "docker/init-production.sh runs `iop --init` (with IRISNAMESPACE=POPHEAT) before `iop --migrate` -- omitted in the plan's action text, but iop's own error message on migrate failure names this exact missing step (IOP support classes not yet loaded in the target namespace)."
  - "CatalogPollingService.Output and ScoreClassifyProcess.Persist use target(\"ScoreClassifyProcess\") / target(\"PersistOperation\") with an explicit default name rather than a bare target(), and PersistOperation uses the embedded-Python object-persistence API instead of iris.sql.exec -- both are required Rule 3 blocking-issue fixes; see Deviations for the full diagnosis."
status: complete
duration: long (multi-hour deep platform-bug diagnosis)
completed: 2026-09-20

coverage:
  - id: D1
    description: "docker compose up -d brings up IRIS Community Edition with a POPHEAT namespace created on first boot, no manual step"
    requirement: INGE-01
    verification:
      - kind: e2e
        ref: "plan 02-01 Task 2 <verify> automated command (docker compose up -d && init-production.sh && SQL count checks)"
        status: pass
    human_judgment: false
  - id: D2
    description: "PopHeat.Production auto-starts on every subsequent container start/restart with zero manual commands (D-05)"
    requirement: INGE-01
    verification:
      - kind: e2e
        ref: "manual docker compose restart iris + iop --status showing Status=running, NeedsUpdate=0, with new Reading rows continuing to accumulate post-restart"
        status: pass
    human_judgment: false
  - id: D3
    description: "PopHeat.Reading and PopHeat.BatchTelemetry exist as SQL-projected IRIS Persistent classes"
    requirement: [INGE-06, TELE-02]
    verification:
      - kind: integration
        ref: "%SYSTEM.OBJ.LoadDir compile output (Load finished successfully) plus SELECT COUNT(*)/SELECT * against both tables via iris sql"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full popularity model: per-category Gaussian curves with midnight-wrapping distance, weekend boost, controlled randomness, [0.02,0.98] clamp rounded to 3 decimals, generic fallback curve for unlisted categories"
    requirement: [POPU-01, POPU-02, POPU-03, POPU-04, POPU-05, POPU-06]
    verification:
      - kind: manual_procedural
        ref: "Live observation of 19 Reading rows across a restart, popularity values (.02-.115) all within range and plausible for a nightclub at ~18:54 (far from its 1h/3h peaks)"
        status: pass
    human_judgment: true
    rationale: "No automated unit tests were written for compute_popularity/classify_heat in this tracer plan (Plan 02-02 extracts them into scoring.py and is the natural place for a test suite); the must_haves backstop truths (MAX-not-SUM for adjacent peaks, extreme-low/high clamp bounds, fast_food-vs-restaurant height ordering) were verified by code review and live spot-checks, not by an executable test asserting the exact numeric contract."
  - id: D5
    description: "Heat classification: nightlife (bar/pub/nightclub) vs daytime thresholds, highest-threshold-first evaluation, BAIXO default"
    requirement: [HEAT-01, HEAT-02, HEAT-04]
    verification:
      - kind: manual_procedural
        ref: "Live Reading rows show HeatLevel=BAIXO for a nightclub venue at a low-popularity hour, consistent with the nightlife scale"
        status: pass
    human_judgment: true
    rationale: "Same as D4 -- no unit test asserts all four threshold boundaries and the BAIXO-on-exception fallback; verified by code review and one live data point only."
  - id: D6
    description: "One real venue from data/venues.json scored, classified, and persisted as a Reading + BatchTelemetry row, insert-only (never UPDATE/DELETE)"
    requirement: [INGE-06, INGE-07, TELE-01, TELE-03]
    verification:
      - kind: e2e
        ref: "plan 02-01 Task 2 <verify> automated command; grep -Eiq '^\\s*(UPDATE|DELETE)\\s' popheat_pipeline/components.py finds nothing; grep for f-string/.format()/%-formatted SQL finds nothing"
        status: pass
    human_judgment: false
  - id: D7
    description: "Package legitimacy verified for iris-pex-embedded-python and tzdata before any install"
    requirement: null
    verification: []
    human_judgment: true
    rationale: "gate=blocking-human checkpoint requiring an actual human decision; per dispatch instructions this was already approved in a prior run of this plan and is recorded here as resolved, not re-verified by this executor."
---

# Phase 2 Plan 1: Docker + IRIS + PopHeat.Production Tracer Summary

**A real `iris-pex-embedded-python` (IoP) production -- CatalogPollingService -> ScoreClassifyProcess -> PersistOperation -- runs inside IRIS Community Edition in Docker, auto-starting on every restart, scoring and persisting one real Porto venue every 3 seconds with the full popularity/heat-classification math.**

## Performance

- **Duration:** Long -- most of the session was spent diagnosing a genuine platform-level bug in the pulled `intersystemsdc/iris-community:latest` image (see Deviations)
- **Tasks:** 2 (Task 1 checkpoint pre-approved, Task 2 tracer fully executed and verified live)
- **Files created:** 8

## Accomplishments

- Docker Compose stack (`docker-compose.yml`) brings up IRIS Community Edition with the `POPHEAT` namespace created on first boot via a CPF `[Actions]` merge file
- `docker/init-production.sh` is a safe-to-re-run one-time setup: installs `iris-pex-embedded-python` + `tzdata`, compiles the two Persistent classes, initializes IoP support classes, migrates `settings.py`, enables auto-start, and starts the production
- `PopHeat.Reading` and `PopHeat.BatchTelemetry` are SQL-projected `%Persistent` classes exactly matching the plan's schema
- `popheat_pipeline/components.py` implements the real, final popularity model (Gaussian per-category curves, midnight-wrapping distance, weekend boost, controlled randomness, clamp+round) and heat classification (nightlife vs daytime thresholds, highest-first evaluation, BAIXO default) -- not placeholders
- Verified live, end-to-end, repeatedly: the production polls `data/venues.json` every 3 seconds, scores/classifies the first venue, and persists a `PopHeat.Reading` row plus a `PopHeat.BatchTelemetry` row -- confirmed across a full `docker compose restart iris` with zero manual intervention (19 rows accumulated across one restart in the final test run)

## Task Commits

1. **Task 1: Package legitimacy check -- iris-pex-embedded-python + tzdata** -- no commit (human-approval checkpoint only; approved in a prior run of this plan before any commits existed, per explicit dispatch instruction; not re-prompted)
2. **Task 2: Docker + IRIS + POPHEAT namespace + PopHeat.Production, one venue end-to-end** -- `89ceee2` (feat)

**Plan metadata:** pending (this SUMMARY.md commit)

## Files Created/Modified

- `docker-compose.yml` -- single `iris` service, official image, bind mount, CPF env var, `restart: unless-stopped`
- `iris/merge.cpf` -- `[Actions]` `CreateDatabase`/`CreateNamespace` for `POPHEAT`
- `docker/init-production.sh` -- one-time setup script (pip install, compile, `iop --init`, `iop --migrate`, `SetAutoStart`, `iop --start`)
- `iris/PopHeat/Reading.cls` -- `%Persistent` class, 8 properties + 2 indices
- `iris/PopHeat/BatchTelemetry.cls` -- `%Persistent` class, 4 properties + 1 index
- `popheat_pipeline/__init__.py` -- package marker
- `popheat_pipeline/components.py` -- `CatalogBatch`/`ScoredBatch` messages, `CatalogPollingService`/`ScoreClassifyProcess`/`PersistOperation`, `compute_popularity`/`classify_heat`/`circular_distance`, `CATEGORY_CURVES`
- `settings.py` -- `Production("PopHeat.Production")` graph, `PRODUCTIONS` list

## Decisions Made

See frontmatter `key-decisions`. In short: the CPF merge mechanism, the missing `iop --init` step, and two runtime framework quirks (`target()` defaults, SQL-vs-object-API for inserts) were all discovered and fixed via live, repeated testing against a real Docker/IRIS stack rather than assumed from documentation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] CPF merge file used the wrong section for namespace/database creation**
- **Found during:** Task 2, first `docker compose up -d`
- **Issue:** The plan's suggested `[Databases]`/`[Namespaces]` raw-section CPF format only *describes* entries expected to already exist in the final `iris.cpf`; it does not *create* a new database. The namespace config entry got registered but `zn "POPHEAT"` failed with `<DIRECTORY>` because the underlying database was never physically created.
- **Fix:** Rewrote `iris/merge.cpf` to use an `[Actions]` section (`CreateDatabase:Name=POPHEAT,Directory=...` / `CreateNamespace:Name=POPHEAT,Globals=POPHEAT,Routines=POPHEAT,Interop=1`) -- confirmed live via the container's own boot log, which explicitly names an "[Actions]" processing phase absent from the raw-section run.
- **Files modified:** `iris/merge.cpf`
- **Verification:** `docker compose exec iris ls /usr/irissys/mgr/popheat` exists after boot; `zn "POPHEAT"` succeeds
- **Committed in:** `89ceee2`

**2. [Rule 3 - Blocking] `CreateDatabase` cannot create multi-level parent directories**
- **Found during:** Task 2, second `docker compose up -d` attempt after fix #1
- **Issue:** Pointing `CreateDatabase` at `/durable/POPHEAT` failed with `ERROR #5032: Cannot create directory '/durable/POPHEAT/` because `/durable` does not pre-exist in the image and `CreateDatabase` only creates one new leaf directory.
- **Fix:** Changed the database directory to `/usr/irissys/mgr/popheat` (parent already exists in every IRIS image).
- **Files modified:** `iris/merge.cpf`
- **Verification:** Database mounts successfully on boot (`Mounted database /usr/irissys/mgr/popheat/ ... read-write`)
- **Committed in:** `89ceee2`

**3. [Rule 3 - Blocking] Missing `iop --init` step before `iop --migrate`**
- **Found during:** Task 2, first successful namespace creation, first migrate attempt
- **Issue:** `iop --migrate settings.py` failed: "IRIS could not find a class required during component registration... this often means the IoP support classes (IOP.Utils, IOP.BusinessService, etc.) are not loaded in the target namespace yet, or migration ran before `iop --init` completed" -- exactly the plan's action text was missing this step.
- **Fix:** Added `export IRISNAMESPACE=POPHEAT` + `iop --init` to `docker/init-production.sh`, run once before the first `iop --migrate`.
- **Files modified:** `docker/init-production.sh`
- **Verification:** `iop --init` loads and compiles all 29 `IOP.*` classes; subsequent `iop --migrate` succeeds
- **Committed in:** `89ceee2`

**4. [Rule 3 - Blocking] `self.Output`/`self.Persist` read back as `""` during polling-triggered calls**
- **Found during:** Task 2, live production ran with zero rows persisted despite `on_poll()` firing correctly every 3 seconds (confirmed via temporary file-write instrumentation, then removed)
- **Issue:** `CatalogPollingService.Output = target()` (bare, no default) resolved to an empty string when read as `self.Output` from inside `on_poll()` -- the live host setting is not hydrated into the Python instance before the timer-triggered call (the polling call path has no underlying IRIS message context, unlike a normal message-dispatched call). This raised `RuntimeError: <SUBSCRIPT>SendRequestAsync+4^Ens.BusinessService.1 ^Ens.Runtime("DispatchName","")` on every poll. Confirmed by temporarily hardcoding the target string, which worked immediately.
- **Fix:** Changed `Output = target()` to `Output = target("ScoreClassifyProcess")`, and defensively also `Persist = target()` to `Persist = target("PersistOperation")` on `ScoreClassifyProcess`. The explicit default is the documented `target(default_name)` pattern from IoP's own cookbooks (used there for a different reason -- a "conventional default route" -- but it also backstops this hydration gap). `settings.py`'s `.connect(...)` calls still govern the real production graph edges; this default is a same-value fallback for the polling-path read.
- **Files modified:** `popheat_pipeline/components.py`
- **Verification:** Live: `on_poll` -> `ScoreClassifyProcess.on_message` -> `PersistOperation.on_message` all fire every 3 seconds after this fix
- **Committed in:** `89ceee2`

**5. [Rule 3 - Blocking] `iris.sql.exec(...)` parameterized INSERT throws `SQLError: <UNIMPLEMENTED>term+110^%qaqpslx` from inside a running Business Operation**
- **Found during:** Task 2, after fix #4 resolved message delivery -- `PersistOperation.on_message` was reached but every `iris.sql.exec` INSERT call raised this SQL-compiler error
- **Issue:** Reproduced consistently: the identical parameterized INSERT statement (same SQL text, same schema) succeeds when run from a standalone `irispython script.py` invocation, but fails every time when executed from inside `PersistOperation`'s own worker process (whether via `on_message` or via an `on_init()` pre-warm attempt using `iris.sql.prepare`, which instead hung the job's own startup). This points to a genuine embedded-SQL query-compiler defect specific to this exact `intersystemsdc/iris-community:latest` (2026.1.0.234.1com) build when compiling a query from inside an Interoperability worker-process context. A separate symptom of the same underlying defect was also observed via `iop --test`/`iop --log`, both of which throw a related `<UNIMPLEMENTED>` error touching `Ens.BP.MasterPendingResponse`.
- **Fix:** Rewrote `PersistOperation.on_message` to use the embedded-Python object-persistence API (`iris.cls("PopHeat.Reading")._New()`, set typed properties, `._Save()`) instead of `iris.sql.exec(...)`. This bypasses the SQL compiler entirely, so it does not hit the defect, and -- as a side benefit -- there is no SQL string to build at all (stronger than parameterized SQL against T-02-01: not even a parameter-binding call surface exists). A `PersistenceError` is raised on any non-OK `%Status` from `._Save()`.
- **Files modified:** `popheat_pipeline/components.py`
- **Verification:** Live, repeatedly: 19 Reading rows + matching BatchTelemetry rows accumulated across a `docker compose restart iris`, with correct field values (Popularity in range, HeatLevel valid, ObservedAt/RecordedAt populated)
- **Committed in:** `89ceee2`

---

**Total deviations:** 5 auto-fixed (all Rule 3 -- blocking issues discovered only through live testing against the real Docker/IRIS stack, not visible from documentation or code review alone)
**Impact on plan:** All five fixes were necessary for the tracer to actually run; none change the plan's architecture (still `service -> process -> operation`, still one venue per poll, still insert-only). Fix #5 changes the *mechanism* of persistence (object API instead of `iris.sql.exec`) but not its safety properties -- if anything it closes the SQL-injection threat (T-02-01) more completely, since no SQL text is built at all. This is a genuine third-party platform defect in the specific pulled image tag, not a code-quality issue; Plan 02-02 (or a later phase) should consider re-testing `iris.sql.exec` if the image is ever repinned to a different build, since the object API works everywhere `iris.sql.exec` does but is marginally more verbose for bulk operations.

## Issues Encountered

- **Flaky first-boot hang (environment-specific, self-healing):** On several `docker compose up -d` cycles from a cold/removed container, the CPF `[Actions]` namespace-activation step entered a tight `Activating Network / Activating new namespace map` retry loop and stalled (observed once as an explicit `ERROR #453: Cannot quiesce the system for namespace reactivation`). In every case, Docker's `restart: unless-stopped` policy automatically restarted the container once, after which it booted cleanly and became `healthy`. This did not require any manual intervention and matches the plan's durability requirement in spirit, but it does mean the very first `docker compose up -d` on a machine may take one extra restart cycle (~30-60s) before the container reports healthy. Not something this plan's code can fix (it is IRIS's own boot-time namespace activation, not `popheat_pipeline` code); flagging for awareness during the live demo -- start the stack a few minutes before judging, not seconds before.

## User Setup Required

None -- no external service configuration required. `data/venues.json` (Phase 1's output, gitignored) must be present at the repo root for `CatalogPollingService` to have data to poll; it already exists on disk from Phase 1 and is not regenerated by this plan.

## Next Phase Readiness

- The full architecture (Docker -> IRIS -> PyProd -> SQL persistence) is proven end-to-end with real, final popularity/classification math -- Plan 02-02 can now safely extend `popheat_pipeline/components.py`/`settings.py` with real batching (150 venues/3s, R1) and full-catalog cycling (R2) without re-touching infra.
- Plan 02-02 should extract `compute_popularity`/`classify_heat`/`circular_distance`/`CATEGORY_CURVES` into `popheat_pipeline/scoring.py` as planned, and this is also the natural place to add the unit tests flagged as a coverage gap in D4/D5 above (the must_haves backstop truths -- MAX-not-SUM, clamp bounds, fast_food-vs-restaurant height ordering -- are implemented but not yet asserted by an executable test).
- Plan 02-02 should also move heat thresholds to `config/heat_thresholds.json` per D-09/D-10 (deferred from this plan, as planned).
- No blockers for Plan 02-02. The five platform-bug workarounds documented above are stable and load-bearing; do not revert them when extending these files.

## Self-Check: PASSED

- All 8 created files verified present on disk.
- Task 2 commit `89ceee2` verified present in `git log --oneline --all`.
- Plan-level `<verification>` re-run: `docker compose up -d` + init + SQL count checks passed (`EXIT:0` equivalent, READING_COUNT=1, TELEMETRY_COUNT=1 on a fresh container); `docker compose restart iris` re-run with no manual step showed `Status: running`, `NeedsUpdate: 0`, and 19 accumulated rows.
- Acceptance-criteria greps re-run: no `UPDATE`/`DELETE` statement in `popheat_pipeline/components.py`; no f-string/`.format()`/`%`-formatted SQL construction.

---
*Phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry*
*Completed: 2026-09-20*
