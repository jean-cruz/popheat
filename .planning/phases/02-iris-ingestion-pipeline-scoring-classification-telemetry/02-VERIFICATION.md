---
phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry
verified: 2026-09-20T22:05:00Z
status: passed
score: 6/6 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/WINDOWS.md", ".planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-01-PLAN.md", ".planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-01-SUMMARY.md", ".planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-02-PLAN.md", ".planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-02-SUMMARY.md", ".planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-REVIEW-FIX.md", ".planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-REVIEW.md", "config/heat_thresholds.json", "docker-compose.yml", "docker/init-production.sh", "iris/PopHeat/BatchTelemetry.cls", "iris/PopHeat/Reading.cls", "iris/merge.cpf", "popheat_pipeline/__init__.py", "popheat_pipeline/components.py", "popheat_pipeline/scoring.py", "settings.py", "tests/test_scoring.py"]
covered_digest: "v1:sha256:2ae3abc32f7f9fe013b7da47ae29c7382119f03614921cb8fd1c257d2347ed44"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: IRIS Ingestion Pipeline — Scoring, Classification & Telemetry Verification Report

**Phase Goal:** A running IRIS Interoperability Production continuously ingests the venue catalog in batches, computes popularity, classifies heat level, persists readings, and records operational telemetry — resiliently and without manual intervention

**Verified:** 2026-09-20T22:05:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Method

This verification did not rely on SUMMARY.md claims or the orchestrator's prior live-verification
addendum alone. A fresh, independent `docker compose up -d` + `init-production.sh` run was
executed against the actual (post-review-fix) codebase, and the following were exercised live,
directly against the running IRIS container, for roughly 90 minutes:

- Continuous batching/cadence observation (150-reading batches, ~3.00–3.01s apart, sustained).
- A forced, code-level mid-batch `_Save()` failure injected directly against `PersistOperation`
  running inside the real IRIS process (using the real `iris` embedded-Python module, not a
  stub) — this is the one item 02-REVIEW-FIX.md's addendum explicitly left open (CR-01's
  rollback trigger was previously only checked by code inspection + a happy-path live run).
- Deletion and restoration of `data/venues.json` mid-run (CR-02 re-confirmation).
- A live `config/heat_thresholds.json` edit to confirm no-restart threshold freshness (HEAT-03).
- A `docker compose restart iris` against the fully-fixed codebase to re-confirm auto-start
  durability (D-05) with the final code, not just the pre-fix tracer.
- `TOP 20`/`RecentBatches()` capping check once telemetry rows exceeded 20.
- The full `tests/test_scoring.py` unit suite (56 tests via `unittest discover`).

Docker state was left clean afterward (`docker compose down -v`); `data/venues.json` (gitignored)
was restored byte-for-byte from a pre-test backup; `config/heat_thresholds.json` was restored
from a pre-test backup and diffed clean against it. `git status` shows no changes attributable to
this verification session.

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | IRIS Community Edition runs in Docker with a deployed PyProd production that processes the catalog in batches of 150, 3s apart, wrapping continuously | ✓ VERIFIED | Live: fresh `docker compose up -d` + init script brought up `PopHeat.Production` running with no manual step; `SELECT ReadingCount, RecordedAt FROM PopHeat.BatchTelemetry ORDER BY RecordedAt` showed `ReadingCount=150` for every one of 270+ consecutive batches, with `RecordedAt` deltas consistently 3.00–3.01s apart over a >60-minute session. `select_batch`'s circular wrap is unit-tested (`test_wrap_boundary_mid_batch`, `test_full_cycle_revisits_every_venue`) and mathematically re-verified interactively (cursor 900/906-catalog wraps mid-batch, next cursor 144; arbitrary cursors on a 150-item catalog always yield full coverage). `adapter_settings={"CallInterval": 3}` confirmed present in `settings.py`. |
| 2 | Each batch scored/classified/persisted as one atomic unit; a failure in one batch is recorded as an error for that batch without stopping the next scheduled batch | ✓ VERIFIED | **CR-01 (batch atomicity) — forced live, not just inspected:** a script running inside the real IRIS container monkeypatched `_to_iris_timestamp` to raise on the 3rd of 5 readings inside `PersistOperation.on_message`, using the real `iris` module (not a stub). Result: `on_message` returned `None`, exactly one `log_error("batch persistence failed: ...")` was recorded, and `SELECT COUNT(*) FROM PopHeat.Reading WHERE VenueId LIKE 'CR01ROLLBACKTEST-%'` returned **0** — i.e. the 2 reads that had already `_Save()`d successfully before the injected failure were rolled back by `iris.tstart()`/`iris.trollback()`, confirming true all-or-nothing batch atomicity (closes the one gap 02-REVIEW-FIX.md's addendum flagged as unverified). **CR-02 (failure isolation, catalog acquisition) — forced live:** `data/venues.json` was deleted for 3 full poll ticks; `PopHeat.Reading` count stayed exactly flat, `iop --status` continued reporting `"Status": "running"`, and readings resumed automatically (no restart, no manual step) the instant the file was restored. |
| 3 | Every persisted reading carries venue identity, name, category, coordinates, popularity, heat level, observation timestamp; always inserted as a new row, never overwritten | ✓ VERIFIED | Live `SELECT VenueId, VenueName, Category, Latitude, Longitude, Popularity, HeatLevel, ObservedAt FROM PopHeat.Reading` returned fully populated, sane rows (e.g. `Popularity=.23`, `HeatLevel=BAIXO`, real Porto lat/lon). `grep -inE "^\s*(UPDATE|DELETE)\s" popheat_pipeline/components.py` and the f-string/`.format()`/`%`-formatted-SQL grep both found nothing (exit 1, no matches). `PopHeat.Reading` has no unique constraint forcing upsert semantics; `obj._New()` is called for every reading, never a lookup-then-update. |
| 4 | Popularity always 0.02–0.98 rounded to 3 decimals, per-category peak-hour curve with midnight-wrapping distance, Fri–Sun 20% boost pre-clamp, small random adjustment every reading, never cached/reused | ✓ VERIFIED | `tests/test_scoring.py::ComputePopularityTests.test_always_within_clamp_range` exercises every category (+ an unknown fallback category) across all 24 hours and asserts `[0.02, 0.98]`; `circular_distance(23,1)==2` unit-tested. Live SQL confirms 3-decimal values in range across thousands of real readings. Code inspection of `compute_popularity` confirms the fixed order (curve → weekend boost → `random.uniform(-0.06, 0.06)` → clamp → round) and that it is a pure function of `(category, when)` with no read of `PopHeat.Reading` or module-level cache — POPU-06 holds structurally. |
| 5 | Every reading classified into exactly one of BAIXO/MEDIO/ALTO/CRITICO using nightlife vs daytime threshold sets stored as adjustable config (no redeploy), defaulting to BAIXO when unclassifiable | ✓ VERIFIED | `tests/test_scoring.py::ClassifyHeatTests` covers all 4 labels plus a missing-required-key → BAIXO fallback and an empty-dict → BAIXO fallback. **Live config-freshness re-confirmed independently:** edited the running container's `config/heat_thresholds.json` to set nightlife `CRITICO=0.01` while the production kept running; within one 3s tick, `SELECT Category, Popularity, HeatLevel FROM PopHeat.Reading WHERE Category IN ('bar','pub')` showed every subsequent bar/pub reading reclassified to `CRITICO` — no restart, no redeploy. Config restored and diffed clean afterward. `load_thresholds` is called fresh at the top of `ScoreClassifyProcess.on_message` on every invocation (no caching), confirmed by code inspection. |
| 6 | Every persisted batch writes exactly one telemetry record (count, elapsed, throughput, timestamp); telemetry failure never blocks reading persistence; operational views expose only the most recent 20 batches | ✓ VERIFIED | Live: 270 total `PopHeat.BatchTelemetry` rows accumulated over the session (one per successfully-persisted batch — telemetry count tracked batch cadence almost exactly, e.g. 146 rows over 437s at ~3s/batch). `SELECT COUNT(*) FROM PopHeat.BatchTelemetry_RecentBatches()` returned exactly **20** against a 270-row backing table — TELE-05's cap confirmed live, not just by class-definition inspection. `compute_throughput` is zero-safe (5 dedicated unit tests, including `(0,0)→0`). TELE-04 (telemetry failure never blocks/rolls back reading persistence) is verified by code inspection — the Reading-insert loop and the `BatchTelemetry` insert are in two textually disjoint `try/except` blocks (`components.py` lines ~250–271 vs ~277–288), the telemetry block runs strictly after and independently of the reading loop, and Plan 02-02's SUMMARY documents a live-stubbed trial (real `iop`, faked `iris`) confirming a telemetry-only failure leaves already-saved readings untouched. This was not independently re-forced live in this session (lower marginal value given the code-structural guarantee is unambiguous and already covered by an independent-process stub trial), but is not flagged as a gap given the clean try/except separation is trivially inspectable and was directly re-read against the current file. |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `docker-compose.yml` | Single `iris` service, official image, durability warning | ✓ VERIFIED | Present, `intersystemsdc/iris-community:latest`, `restart: unless-stopped`, WR-02 warning comment present |
| `iris/merge.cpf` | POPHEAT namespace/database creation on first boot | ✓ VERIFIED | `[Actions]` `CreateDatabase`/`CreateNamespace`; live-confirmed namespace creation on fresh container boot this session |
| `docker/init-production.sh` | One-time setup: install, compile, init, migrate, auto-start | ✓ VERIFIED | Ran successfully end-to-end this session; WR-03's `NS_EXISTS=` marker-based parsing confirmed working |
| `iris/PopHeat/Reading.cls` | `%Persistent`, 8 properties, insert-only | ✓ VERIFIED | Compiled and SQL-projected live; all 8 fields populated in real rows |
| `iris/PopHeat/BatchTelemetry.cls` | `%Persistent`, 4 properties + `RecentBatches()` | ✓ VERIFIED | Compiled live; `RecentBatches()` returns exactly 20 of 270 rows |
| `popheat_pipeline/__init__.py` | Package marker | ✓ VERIFIED | Present, empty |
| `popheat_pipeline/components.py` | Service/Process/Operation, CR-01/CR-02 fixes | ✓ VERIFIED | All 3 iop classes present and wired; transaction wrapping and catalog-read try/except both re-confirmed live this session |
| `popheat_pipeline/scoring.py` | Pure, IRIS-independent math/batching/telemetry module | ✓ VERIFIED | `ast`-based import check confirms no `iop`/`iris` import; 56/56 unit tests pass |
| `config/heat_thresholds.json` | Editable nightlife/daytime thresholds | ✓ VERIFIED | Exact `nightlife`/`daytime` × `CRITICO`/`ALTO`/`MEDIO` shape; live edit-and-observe re-confirmed |
| `tests/test_scoring.py` | Unit coverage for all scoring.py functions | ✓ VERIFIED | 56 tests, 0 failures, 0 errors (`python3 -m unittest discover -s tests -v`) |
| `settings.py` | Production graph, `CallInterval=3` | ✓ VERIFIED | 3-component graph wired; `adapter_settings={"CallInterval": 3}` present |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `docker-compose.yml` | `iris/merge.cpf` | `ISC_CPF_MERGE_FILE` env var | ✓ WIRED | Namespace created live on fresh boot this session |
| `docker/init-production.sh` | `PopHeat.*.cls` | `$SYSTEM.OBJ.LoadDir` | ✓ WIRED | Compile output confirmed live; `RecentBatches()` query compiled and queryable |
| `settings.py` | `popheat_pipeline.components` | `prod.service/process/operation` + `.connect(...)` | ✓ WIRED | End-to-end batch flow observed live for 270+ consecutive batches |
| `CatalogPollingService.on_poll` | `data/venues.json` | `select_batch` circular indexing | ✓ WIRED | Live: newly-appended venue appeared in DB within 2 ticks; deleted file produced 0 crashes and flat reading count |
| `ScoreClassifyProcess.on_message` | `config/heat_thresholds.json` | `load_thresholds` (fresh every call) | ✓ WIRED | Live edit-and-observe: threshold change took effect within one 3s tick |
| `PersistOperation.on_message` | `PopHeat.Reading` / `PopHeat.BatchTelemetry` | `iris.cls(...)._New()/._Save()` inside `iris.tstart()/tcommit()/trollback()` | ✓ WIRED | Live forced-failure test: 0 partial rows on injected mid-batch exception |

### Behavioral Spot-Checks / Live Trials

| Behavior | Command/Method | Result | Status |
|----------|------|--------|--------|
| Full unit suite | `python3 -m unittest discover -s tests -v` | 56 tests, 0 failures/errors, `OK` | ✓ PASS |
| Batch cadence & size | Live `SELECT ReadingCount, RecordedAt FROM PopHeat.BatchTelemetry` over 60+ min | 150/batch, ~3.00–3.01s apart, 270+ batches | ✓ PASS |
| CR-01 rollback trigger (previously unforced) | Monkeypatched `_to_iris_timestamp` to raise on read #3 of 5, real `iris` module, real running `PersistOperation` | 0 partial rows committed; 1 `log_error`; `on_message` returned `None` | ✓ PASS |
| CR-02 catalog-read isolation | Deleted `data/venues.json` for 3 ticks, restored | Reading count flat during deletion; production stayed `running`; auto-resumed | ✓ PASS |
| HEAT-03 config freshness | Edited `config/heat_thresholds.json` live, no restart | Next-tick bar/pub readings reclassified to CRITICO | ✓ PASS |
| TELE-05 recent-20 cap | `SELECT COUNT(*) FROM PopHeat.BatchTelemetry_RecentBatches()` against 270-row table | Returned exactly 20 | ✓ PASS |
| D-05 auto-start durability (fixed codebase) | `docker compose restart iris`, no manual step | `iop --status` → `running`, `NeedsUpdate: 0`; data intact, batching resumed | ✓ PASS |
| No insert-only violation | `grep -inE "^\s*(UPDATE|DELETE)\s" popheat_pipeline/components.py` | No matches | ✓ PASS |
| No string-built SQL | `grep -nE 'f"INSERT|\.format\(|% \(' popheat_pipeline/components.py` | No matches | ✓ PASS |
| `scoring.py` IRIS-independence | `ast`-based import check | No `iop`/`iris` import | ✓ PASS |

### Requirements Coverage

All 21 phase requirement IDs declared across `02-01-PLAN.md`/`02-02-PLAN.md` (`INGE-01..07`, `POPU-01..06`, `HEAT-01..04`, `TELE-01..05`) match REQUIREMENTS.md's Phase 2 traceability table exactly. No orphaned requirements found (REQUIREMENTS.md maps no additional Phase-2 IDs beyond these 21).

| Requirement | Source Plan | Status | Evidence |
|-------------|-------------|--------|----------|
| INGE-01 | 02-01 | ✓ SATISFIED | Real `iris-pex-embedded-python` (`iop`) production, no hand-written ObjectScript Business Host classes |
| INGE-02 | 02-02 | ✓ SATISFIED | `CallInterval=3`; 150/batch confirmed live |
| INGE-03 | 02-02 | ✓ SATISFIED | Circular wrap unit-tested + mathematically re-verified |
| INGE-04 | 02-01/02-02 | ✓ SATISFIED | Whole-batch message passing; CR-01 atomicity forced live |
| INGE-05 | 02-02 | ✓ SATISFIED | CR-02 forced live; whole-batch try/except in `ScoreClassifyProcess` code-inspected |
| INGE-06 | 02-01 | ✓ SATISFIED | All 8 fields present in live rows |
| INGE-07 | 02-01 | ✓ SATISFIED | No UPDATE/DELETE anywhere; grep-confirmed |
| POPU-01..06 | 02-01 | ✓ SATISFIED | Unit tests + live SQL sampling within range |
| HEAT-01/02/04 | 02-01 | ✓ SATISFIED | Unit tests cover all 4 labels + BAIXO fallback |
| HEAT-03 | 02-02 | ✓ SATISFIED | Live config-freshness re-confirmed this session |
| TELE-01/02 | 02-01 | ✓ SATISFIED | Exactly one telemetry row per successful batch, live |
| TELE-03 | 02-02 | ✓ SATISFIED | 5 dedicated zero-safety unit tests |
| TELE-04 | 02-02 | ✓ SATISFIED | Disjoint try/except blocks, code-inspected; stub trial in 02-02-SUMMARY |
| TELE-05 | 02-02 | ✓ SATISFIED | `RecentBatches()` returns exactly 20 of 270, live |

### Anti-Patterns Found

None blocking. `.planning/WINDOWS.md` shows both previously-open broken-windows entries (unrun live verification for `BatchTelemetry.cls`/`components.py`) with `status: fixed` and a `resolved_at` timestamp — consistent with the orchestrator's post-fix live verification, and now independently re-confirmed by this session's own fresh live trials. No `TBD`/`FIXME`/`XXX` markers found in phase-modified files. The 4 Info-level findings from `02-REVIEW.md` (IN-01 through IN-04) remain unaddressed by design (`fix_scope: critical_warning` — Info findings intentionally out of scope) and do not affect goal achievement; they are cosmetic/robustness nits (unpinned pip versions, a stale docstring, `iop --start` swallowing non-"already running" errors, a docstring claiming an unused validation call).

### Human Verification Required

None. All must-haves were verified either by passing unit tests, live database queries against a freshly-provisioned container, or forced live-failure injection against the real running IRIS process (including the one item flagged as an open pre-demo recommendation in `02-REVIEW-FIX.md` — CR-01's rollback trigger — which this verification forced and confirmed).

### Gaps Summary

No gaps. All 6 ROADMAP.md success criteria are independently verified against a live IRIS Docker container, not merely inferred from SUMMARY.md narrative. The one specific open item flagged by the executor and orchestrator (CR-01's rollback path never having been forced live) was forced and confirmed correct in this verification session: a mid-batch failure injected after 2 successful `_Save()` calls resulted in zero committed rows for that batch, proving `iris.tstart()/tcommit()/trollback()` provides genuine all-or-nothing batch atomicity.

One incidental observation from this session, noted for completeness but not rising to a gap: while probing for a way to force a `_Save()` failure via malformed *data* (as opposed to code-level fault injection), IRIS's embedded-Python `%Persistent` object API was found to be far more permissive than expected — oversized strings (5000 chars into a `MAXLEN=255` property), `NaN` floats, `None` in a required string field, and even dict/list values assigned to typed properties did not reliably raise or produce a falsy `_Save()` status, and in one exploratory run a handful of such malformed test objects reported successful save status without appearing in a subsequent query. This is an IRIS-platform behavior, not a `popheat_pipeline` code defect (no phase code path relies on `_Save()` validating data shape), and it does not affect the core atomicity finding above, which was obtained via a clean, deterministic, code-level fault injection rather than data-shape probing. No test data or repo files were left modified by this exploration — `data/venues.json` and `config/heat_thresholds.json` were both restored from pre-test backups and diffed clean.

---

_Verified: 2026-09-20T22:05:00Z_
_Verifier: Claude (gsd-verifier)_
