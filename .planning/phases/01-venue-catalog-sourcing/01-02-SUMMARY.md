---
phase: 01-venue-catalog-sourcing
plan: 2
subsystem: data-ingestion
tags: [python, dedup, unittest, decimal-rounding, tdd]

requires:
  - phase: 01-venue-catalog-sourcing (plan 01-01)
    provides: "scripts/build_catalog.py's pure functions (load_config, build_overpass_query, fetch_overpass, map_element_to_venue, write_json_atomic) and its main() orchestration"
provides:
  - "round5(value): explicit decimal round-half-up to 5 decimal places"
  - "dedupe_venues(venues): first-occurrence-wins dedup on (name, round5(lat), round5(lon)), order-preserving"
  - "run(config_path, fetch_fn=fetch_overpass, catalog_path=CATALOG_PATH, raw_path=RAW_SNAPSHOT_PATH): testable orchestration function, main() reduced to an argparse wrapper around it"
affects: [phase-02-iris-pyprod-pipeline]

actuals:
  tokens: 2808
  tasks: 2
  commits: 4

tech-stack:
  added: []
  patterns:
    - "TDD RED-GREEN per task: tests committed first (confirmed failing via ImportError), then implementation committed separately"
    - "decimal.Decimal(str(value)).quantize(..., ROUND_HALF_UP) for the dedup rounding key — never Python's native round() (round-half-to-even on floats)"
    - "Dependency-injected fetch_fn/catalog_path/raw_path parameters on run() so orchestration is testable without touching the network or real data/ directory"

key-files:
  created: []
  modified:
    - scripts/build_catalog.py
    - tests/test_build_catalog.py

key-decisions:
  - "Followed the plan's exact function signatures and wiring points (round5, dedupe_venues, run()) with no naming deviations."
  - "Did a full RED-GREEN cycle per task despite the plan's frontmatter being type: execute (not type: tdd) — no gate enforcement required, but the tasks carry tdd=\"true\" and RED was mechanically achievable this time (unlike Plan 01-01's tracer-first Task 2), so it was followed for real."

patterns-established: []

requirements-completed: [VENU-04, VENU-05, VENU-06]

coverage:
  - id: D1
    description: "round5() and dedupe_venues() implement the VENU-04 5-decimal-coordinate dedup rule (first-occurrence-wins, order-preserving, case-sensitive name match) and are wired into run()'s pipeline between filtering and catalog write"
    requirement: "VENU-04"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_round5_half_up_tie"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_dedupe_empty_and_single"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_dedupe_drops_boundary_duplicate"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_dedupe_case_sensitive_names_not_merged"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_dedupe_keeps_first_id_on_collision"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_dedupe_preserves_survivor_order"
        status: pass
      - kind: other
        ref: "python3 scripts/build_catalog.py --config config/catalog_build.json; DEDUP_OK shape-check on data/venues.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "run() is extracted from main() and independently testable via injected fetch_fn/catalog_path/raw_path; a zero-match Overpass success is never confused with a failure, a failed fetch never touches an existing catalog, and successive successful runs fully replace prior content (VENU-06 empty/overwrite semantics)"
    requirement: "VENU-06"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_run_empty_overpass_result_writes_empty_catalog_and_exits_zero"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_run_fetch_failure_leaves_existing_catalog_untouched_and_exits_nonzero"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_run_second_call_fully_overwrites_first"
        status: pass
      - kind: other
        ref: "python3 scripts/build_catalog.py --config config/catalog_build.json; echo EXIT:$? (live end-to-end run after refactor, exits 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Stable venue identity survives deduplication — on collision, the FIRST candidate's id (and full record) is kept, never the second's (VENU-05 adjacency)"
    requirement: "VENU-05"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_dedupe_keeps_first_id_on_collision"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-09-20
status: complete
---

# Phase 1 Plan 2: Venue Catalog Deduplication + Testable run() Summary

**5-decimal-coordinate dedup (`round5`/`dedupe_venues`) wired into `build_catalog.py`'s write path, plus an extracted `run()` orchestration function that mechanically proves zero-match success, fetch-failure preservation, and full-overwrite semantics — closing VENU-04 through VENU-06.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-09-20T13:45:00Z
- **Completed:** 2026-09-20T13:59:56Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `round5(value)` — explicit `decimal.Decimal(str(value)).quantize(..., ROUND_HALF_UP)` rounding to 5 decimal places, deliberately avoiding Python's native `round()` (round-half-to-even on binary floats).
- `dedupe_venues(venues)` — first-occurrence-wins deduplication keyed on `(name, round5(lat), round5(lon))`, preserving survivor order (no sorting), keeping the first candidate's `id` on collision.
- `dedupe_venues` wired into the write pipeline between `map_element_to_venue` filtering and the catalog write; the run-summary line now reports `dropped (duplicate): N`.
- `run(config_path, fetch_fn=fetch_overpass, catalog_path=CATALOG_PATH, raw_path=RAW_SNAPSHOT_PATH)` extracted from `main()`, taking dependency-injected `fetch_fn`/`catalog_path`/`raw_path` so tests exercise the full orchestration offline; `main()` reduced to `argparse` + `return run(args.config)`.
- 9 new unit tests (6 dedup/round5, 3 `run()`-level) added to `BuildCatalogTests`, all following a real RED (confirmed `ImportError` before implementation) → GREEN cycle; full suite is 20/20 passing.
- Live re-run against overpass-api.de after both refactors still exits 0 and produces a 906-venue `data/venues.json` with zero `(name, rounded-lat, rounded-lon)` collisions (the live dataset for this bbox happens to contain no exact-name-and-coordinate duplicates today — the dedup logic is proven by the unit tests' synthetic collision cases, and by the live run producing `dropped (duplicate): 0` with a verified-collision-free output).

## Task Commits

Each task followed a RED → GREEN cycle, committed separately:

1. **Task 1: round5 + dedupe_venues (RED)** - `188f26b` (test)
2. **Task 1: round5 + dedupe_venues (GREEN)** - `9dededf` (feat)
3. **Task 2: extract run() (RED)** - `9b086e6` (test)
4. **Task 2: extract run() (GREEN)** - `7bd4bc5` (feat)

**Plan metadata:** committed separately per worktree-mode protocol (SUMMARY.md + REQUIREMENTS.md only; STATE.md/ROADMAP.md owned by the orchestrator)

## Files Created/Modified
- `scripts/build_catalog.py` - Adds `round5`, `dedupe_venues`; extracts `run()` from `main()`; `main()` reduced to an `argparse` wrapper
- `tests/test_build_catalog.py` - Adds 9 test methods (6 dedup/round5, 3 `run()`-level) to `BuildCatalogTests`

## Decisions Made
- Followed the plan's exact function signatures and wiring points (`round5`, `dedupe_venues`, `run()`) with no naming deviations.
- Ran a genuine RED→GREEN cycle per task (test commit confirmed failing via `ImportError`, then implementation commit), since — unlike Plan 01-01's Task 2 — these tests describe behavior that did not yet exist, making a true RED phase mechanically straightforward.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`data/venues.json` now satisfies VENU-01 through VENU-06 in full: eligible, deduplicated, config-scoped, stably-identified venues, written by an on-demand CLI run with mechanically-proven zero-match and repeated-run edge-case behavior. Phase 1 is complete. Phase 2 (IRIS PyProd ingestion pipeline) can read `data/venues.json` as its sole input with no further catalog-side work required.

No blockers. Note for Phase 2: the live catalog currently contains 906 venues (0 duplicates dropped on the current live OSM snapshot for this bbox) — the dedup logic exists and is proven correct by unit tests, but has not yet had an opportunity to drop anything from a real Overpass response for this specific bounding box.

---
*Phase: 01-venue-catalog-sourcing*
*Completed: 2026-09-20*

## Self-Check: PASSED

- Both modified files verified present on disk (scripts/build_catalog.py, tests/test_build_catalog.py).
- All 4 commits verified in `git log`: `188f26b` (Task 1 RED), `9dededf` (Task 1 GREEN), `9b086e6` (Task 2 RED), `7bd4bc5` (Task 2 GREEN).
- Re-ran unit tests (`python3 -m unittest tests.test_build_catalog`): 20/20 pass.
- Re-ran plan-level `<verification>`: live run exits 0, `data/venues.json` (906 entries) has zero `(name, round(lat,5), round(lon,5))` key collisions (`DEDUP_OK`).
- Re-ran all task-level `<acceptance_criteria>` for both tasks: all pass (grep confirms `dedupe_venues` def + call site; `run()`/`main()` signatures match spec exactly).
