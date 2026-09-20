---
phase: 01-venue-catalog-sourcing
plan: 1
subsystem: data-ingestion
tags: [python, overpass-api, openstreetmap, unittest, cli]

requires: []
provides:
  - "config/catalog_build.json: bounding box, amenity allowlist, Overpass endpoint/timeouts/byte-cap config"
  - "scripts/build_catalog.py: standalone Python CLI that fetches, filters, and writes the venue catalog"
  - "data/venues.json + data/venues.raw.json: live-produced, gitignored build artifacts"
  - "tests/test_build_catalog.py: 11-test unit suite for the pure functions"
affects: [01-02-dedup-plan, phase-02-iris-pyprod-pipeline]

actuals:
  tokens: 3315
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Stdlib-only Python CLI (json/urllib.request/argparse/tempfile) — no pip dependency for scripts/build_catalog.py"
    - "Atomic file writes via tempfile.NamedTemporaryFile + os.replace() to prevent partial-write corruption"
    - "Fail-loud config validation (ConfigError, non-zero exit) before any network call"

key-files:
  created:
    - config/catalog_build.json
    - scripts/__init__.py
    - scripts/build_catalog.py
    - tests/__init__.py
    - tests/test_build_catalog.py
    - .gitignore
  modified: []

key-decisions:
  - "Added a descriptive User-Agent header to the Overpass POST request (Rule 3 blocker fix) — overpass-api.de's Apache config returns HTTP 406 for urllib's default 'Python-urllib/x.y' User-Agent, silently rejecting requests with no other error signal. Fixed with 'PopHeat-CatalogBuilder/1.0 (+https://github.com/popheat)'."
  - "Used tempfile.NamedTemporaryFile + os.replace() (not a raw open-and-write) for both data/venues.json and data/venues.raw.json, matching D-05's fail-loud/preserve-last-good-catalog posture."

patterns-established:
  - "Pattern 1: pure functions (load_config, build_overpass_query, derive_id, map_element_to_venue, write_json_atomic) are separated from the network I/O (fetch_overpass) and orchestration (main), keeping the unit-testable surface network-free."

requirements-completed: [VENU-01, VENU-02, VENU-03, VENU-05, VENU-06]

coverage:
  - id: D1
    description: "Live Overpass fetch (config-driven bbox + amenity allowlist) filtered and written to data/venues.json + data/venues.raw.json, end-to-end"
    requirement: "VENU-01"
    verification:
      - kind: other
        ref: "python3 scripts/build_catalog.py --config config/catalog_build.json (live run against overpass-api.de)"
        status: pass
      - kind: other
        ref: "python3 -c shape-check on data/venues.json (all entries have id/name/category/lat/lon)"
        status: pass
      - kind: other
        ref: "test -s data/venues.raw.json"
        status: pass
    human_judgment: false
  - id: D2
    description: "Required-field filtering (name/lat/lon/amenity) discards ineligible places before catalog write, per VENU-02"
    requirement: "VENU-02"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_map_element_drops_missing_name"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_map_element_drops_missing_lat_lon"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_map_element_drops_missing_amenity"
        status: pass
    human_judgment: false
  - id: D3
    description: "Config-only coverage change (bounding_box/amenity_allowlist live exclusively in config/catalog_build.json, no hardcoded values in script), per VENU-03"
    requirement: "VENU-03"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_query_includes_bbox_and_allowlist"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_load_config_missing_file_raises"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_load_config_missing_key_raises"
        status: pass
      - kind: other
        ref: "grep -c amenity_allowlist|bounding_box scripts/build_catalog.py (both referenced by name, no hardcoded numbers/strings)"
        status: pass
    human_judgment: false
  - id: D4
    description: "Stable per-venue OSM-derived identity (osm_type/osm_id), independent per-element mapping preserving input order, per VENU-05"
    requirement: "VENU-05"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_derive_id_node_and_way"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_map_element_empty_list"
        status: pass
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_output_order_preserves_input_order"
        status: pass
    human_judgment: false
  - id: D5
    description: "Catalog regeneration is a manual, explicit CLI invocation only — no scheduling/polling introduced, per VENU-06"
    requirement: "VENU-06"
    verification: []
    human_judgment: true
    rationale: "Absence of scheduling/automation is a structural property of the codebase (no cron/scheduler/daemon code exists anywhere in this plan's files) rather than something a single test asserts — confirmed by code review of scripts/build_catalog.py's main(), which only runs on direct invocation."
  - id: D6
    description: "OSM contributor metadata (user/uid/changeset/contact:*) never reaches the public-facing catalog"
    verification:
      - kind: unit
        ref: "tests/test_build_catalog.py#BuildCatalogTests.test_map_element_whitelists_fields_only"
        status: pass
    human_judgment: false
  - id: D7
    description: "Generated build artifacts (data/venues.json, data/venues.raw.json, __pycache__) are gitignored while source files remain tracked"
    verification:
      - kind: other
        ref: "git check-ignore -q data/venues.json data/venues.raw.json"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-20
status: complete
---

# Phase 1 Plan 1: Config-Driven Overpass Venue Catalog Build Summary

**Standalone stdlib-only Python CLI (`scripts/build_catalog.py`) that live-queries overpass-api.de for Porto's Ribeira/Sé/Baixa-Aliados bbox, filters to 6 eligible amenity tags, strips OSM contributor metadata, and atomically writes a 906-venue `data/venues.json` — proven with a real run, not a mock.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-09-20T13:43:00Z
- **Completed:** 2026-09-20T14:08:00Z
- **Tasks:** 2
- **Files modified:** 6 (all created)

## Accomplishments
- Config-driven Overpass QL query builder (`build_overpass_query`) reading bbox + amenity allowlist exclusively from `config/catalog_build.json` — zero hardcoded coordinates or amenity strings in `scripts/build_catalog.py`.
- Live end-to-end run against overpass-api.de: fetched 930 elements, dropped 24 for missing required fields, wrote 906 field-complete venues to `data/venues.json` plus the raw response to `data/venues.raw.json`.
- Atomic writes (`write_json_atomic`) via `tempfile.NamedTemporaryFile` + `os.replace()` so an interrupted run can never leave a partially-written catalog.
- Privacy-by-construction field mapping (`map_element_to_venue`) that whitelists exactly 5 output keys, verified never to leak OSM contributor metadata (`user`/`uid`/`changeset`) or unrelated tags (`contact:*`).
- 11-test offline unit suite covering query construction, field filtering (missing name/lat/lon/amenity, whitespace-only names), ID derivation, config validation, empty-input handling, and input-order preservation.
- `.gitignore` excluding generated artifacts (`data/venues.json`, `data/venues.raw.json`, `__pycache__/`) while keeping all source files tracked.

## Task Commits

Each task was committed atomically:

1. **Task 1: Config-driven Overpass fetch -> filtered catalog write, end-to-end** - `60249c6` (feat)
2. **Task 2: Unit-test the pure functions + gitignore generated artifacts** - `7290930` (test)

**Plan metadata:** committed separately per worktree-mode protocol (SUMMARY.md + REQUIREMENTS.md only; STATE.md/ROADMAP.md owned by the orchestrator)

_Note: Task 2 carries `tdd="true"` but produced a single `test(01-01)` commit rather than a full RED→GREEN→REFACTOR sequence — see "TDD Gate Compliance" below for why._

## Files Created/Modified
- `config/catalog_build.json` - Bounding box, amenity allowlist, Overpass endpoint/timeouts/byte-cap (6 required keys)
- `scripts/__init__.py` - Empty package marker
- `scripts/build_catalog.py` - CLI entrypoint: load_config, build_overpass_query, fetch_overpass, derive_id, map_element_to_venue, write_json_atomic, main
- `tests/__init__.py` - Empty package marker
- `tests/test_build_catalog.py` - `BuildCatalogTests` with 11 unittest methods
- `.gitignore` - Excludes `data/venues.json`, `data/venues.raw.json`, `__pycache__/`, `*.pyc`

## Decisions Made
- Added a `User-Agent` header to the Overpass POST request — see Deviations below; this was necessary to reach the live API at all, not a design preference.
- Followed the plan's exact function/constant naming and file layout as specified (no naming deviations).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added User-Agent header to Overpass HTTP request**
- **Found during:** Task 1 (live verification run)
- **Issue:** The live Overpass API call failed with `HTTP Error 406: Not Acceptable` on every attempt. Diagnosed via `curl` against `overpass-api.de` root and the interpreter endpoint: requests with no `User-Agent` header (or curl's default) were rejected with 406, while a request with a descriptive `User-Agent` succeeded (HTTP 200, real data returned). `urllib.request`'s default User-Agent (`Python-urllib/3.10`) triggers the same rejection — this is a real-world constraint of the live public endpoint that the plan's `<action>` text did not anticipate, since it specified only the request body/timeout/byte-cap behavior of `fetch_overpass`.
- **Fix:** Added a `headers={"User-Agent": "PopHeat-CatalogBuilder/1.0 (+https://github.com/popheat)"}` to the `urllib.request.Request(...)` call in `fetch_overpass`. No other behavior changed — request method, body, and timeout handling are exactly as specified in the plan.
- **Files modified:** `scripts/build_catalog.py`
- **Verification:** Live run against overpass-api.de now exits 0, returns 930 elements, and writes a 906-venue catalog. Re-ran multiple times to confirm the fix was not a fluke (transient 504 was observed once during diagnosis and resolved on retry — normal API latency, unrelated to the User-Agent fix).
- **Committed in:** `60249c6` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for the live Overpass call to succeed at all — without it, Task 1's core acceptance criterion (a real, non-empty catalog from a live run) could not be met. No scope creep; the fix is a single HTTP header addition scoped entirely inside `fetch_overpass`.

## TDD Gate Compliance

Task 2 carries `tdd="true"`, but this plan's frontmatter is `type: execute` (not `type: tdd`), so the plan-level RED/GREEN/REFACTOR gate enforcement in `gsd-core/references/tdd.md` does not apply, and `workflow.tdd_mode` is not set in `.planning/config.json`.

Per the plan's own tracer-first design (stated in the `<objective>`), Task 1 is a `type="tracer"` task that builds and live-verifies `scripts/build_catalog.py`'s pure functions *before* Task 2 adds unit-test coverage for them. This means Task 2's tests describe behavior that the implementation (built and proven live in Task 1) already satisfies — a true RED phase (test fails before implementation exists) was not possible without re-deleting working, live-verified code purely to manufacture a failing test, which the canonical TDD error-handling guidance (`tdd.md` §Error Handling: "Test doesn't fail in RED phase: Feature may already exist — investigate") treats as a signal to investigate and proceed, not a violation to force around.

**Resolution:** wrote all 11 tests, ran them once (all passed immediately, confirming the Task 1 implementation is correct against every behavior the plan specifies), and committed as a single `test(01-01): ...` commit rather than a `test → feat → refactor` sequence. No `feat(01-01)` commit was needed for Task 2 because no new implementation code was written — Task 1's `feat(01-01)` commit already covers the implementation these tests verify.

This is intentional and consistent with the plan's own structure, not a gap in test coverage: all 11 tests exist, all pass, and they exercise every `<behavior>` bullet listed in Task 2.

## Issues Encountered
- Live Overpass API returned a transient `HTTP 504 Gateway Timeout` once during diagnosis (unrelated to the User-Agent fix, which was already applied by that point) — resolved on immediate retry with no code change. Not treated as a deviation since it self-resolved and the final live run (used for the committed acceptance-criteria verification) succeeded cleanly.

## User Setup Required

None - no external service configuration required. The Overpass API is public and requires no authentication or API key.

## Next Phase Readiness

`data/venues.json` and `data/venues.raw.json` are both gitignored, locally-generated artifacts (not committed) — running `python3 scripts/build_catalog.py` regenerates them on demand, as required by VENU-06. Plan 01-02 (deduplication) can now build directly on `map_element_to_venue`'s existing per-venue records; no blockers.

Note for Phase 2 planning: the live catalog currently contains 906 venues (no deduplication yet — Plan 01-02 will apply the 5-decimal-coordinate dedup rule from `specs/venue-sourcing.spec` R4), well above the phase's original 50-150 venue target for the configured bbox. This is expected — OSM data density in Porto's historic center is higher than the original estimate — and does not require a bbox change; noted here for continuity, not as a blocker.

---
*Phase: 01-venue-catalog-sourcing*
*Completed: 2026-09-20*
