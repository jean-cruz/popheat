---
phase: 01-venue-catalog-sourcing
verified: 2026-09-20T11:30:00Z
status: passed
score: 6/6 must-haves verified
covered_files: [".gitignore", ".planning/REQUIREMENTS.md", ".planning/phases/01-venue-catalog-sourcing/01-01-PLAN.md", ".planning/phases/01-venue-catalog-sourcing/01-01-SUMMARY.md", ".planning/phases/01-venue-catalog-sourcing/01-02-PLAN.md", ".planning/phases/01-venue-catalog-sourcing/01-02-SUMMARY.md", ".planning/phases/01-venue-catalog-sourcing/01-REVIEW-FIX.md", ".planning/phases/01-venue-catalog-sourcing/01-REVIEW.md", "config/catalog_build.json", "scripts/__init__.py", "scripts/build_catalog.py", "tests/__init__.py", "tests/test_build_catalog.py"]
covered_digest: "v1:sha256:dd37d14fb732fe9284dbeac6d12bdb4c35ec40fcd955e55abe12d58b9287d329"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 5/6
  gaps_closed:
    - "A failed Overpass fetch leaves the existing data/venues.json catalog untouched, distinct from a genuine zero-match success (VENU-06 failure/empty distinction, CR-01)"
  gaps_remaining: []
  regressions: []
---

# Phase 1: Venue Catalog Sourcing Verification Report

**Phase Goal:** A real, deduplicated venue catalog for one city bounding box exists for the pipeline to ingest
**Verified:** 2026-09-20T11:30:00Z
**Status:** passed
**Re-verification:** Yes — after gap closure (`/gsd-code-review 01 --fix`, commit f33af38 for the blocking gap plus 5 warning-level fixes)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Catalog build against OSM for the configured bbox yields only bar/pub/restaurant/cafe/fast_food/nightclub-tagged venues; changing the bbox is config-only | ✓ VERIFIED | `build_overpass_query`/`map_element_to_venue` build the regex/bbox/allowlist check exclusively from `config["amenity_allowlist"]`/`config["bounding_box"]`; `grep` for literal coordinate/amenity strings in `scripts/build_catalog.py` returns zero hits. Live re-run today against overpass-api.de produced 906 venues; every entry's `category` ⊆ `{bar,pub,restaurant,cafe,fast_food,nightclub}` and every lat/lon falls within the configured bbox (verified programmatically). |
| 2 | Places missing name, latitude, longitude, or amenity tag are excluded from the catalog | ✓ VERIFIED | `map_element_to_venue` returns `None` for missing/empty/whitespace-only name, missing/out-of-allowlist amenity, and missing lat/lon/center. Live run today: 24 of 930 fetched elements dropped for missing fields; 0 of the 906 surviving entries have an empty/whitespace-only name. |
| 3 | No two catalog entries share the same name and coordinates rounded to 5 decimal places | ✓ VERIFIED | `dedupe_venues` keyed on `(name, round5(lat), round5(lon))`, first-occurrence-wins, order-preserving; `round5` uses explicit `decimal.Decimal(...).quantize(..., ROUND_HALF_UP)`. Live run today: 906-entry `data/venues.json` has zero key collisions (verified programmatically). |
| 4 | Every catalog venue carries a stable identifier derived from its OSM source record | ✓ VERIFIED | `derive_id(element)` returns `f"{element['type']}/{element['id']}"`. Live catalog: all 906 `id` values are non-empty and contain a `/` separating OSM type from numeric id. |
| 5 | The catalog is produced by an on-demand build step, not recomputed automatically on every ingestion cycle | ✓ VERIFIED | `grep -i "schedule\|cron\|while True\|daemon\|watch"` against `scripts/build_catalog.py` returns zero hits — no scheduler/loop/daemon code exists anywhere in the phase's files; `main()`/`run()` execute exactly once per invocation and return. |
| 6 | A failed Overpass fetch leaves the existing catalog untouched, distinct from a genuine zero-match success (VENU-06 failure/empty distinction — CR-01) | ✓ VERIFIED | **Gap closed.** `run()` (line ~301) now checks `if "elements" not in response: raise OverpassFetchError(...)` immediately after the fetch call and before any write, routing the soft-failure through the existing `except OverpassFetchError` handler (prints `ERROR: ...`, returns 1, never calls `write_json_atomic`). Independently reproduced the exact scenario from the prior failed verification: injected a fake `fetch_fn` returning `{"version": 0.6, "remark": "runtime error: Query timed out"}` (no `elements` key) against a `catalog_path` pre-seeded with one existing venue — result: `exit_code: 1`, catalog file byte-identical to its pre-seeded content, no raw snapshot written. Also covered by the new regression test `test_run_missing_elements_key_treated_as_failure_not_zero_match`, which passes. |

**Score:** 6/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/catalog_build.json` | Bounding box, amenity allowlist, Overpass endpoint/timeouts/byte-cap (6 keys) | ✓ VERIFIED | All 6 required keys present with correct types/values; consumed by `load_config`, which now also validates value types (WR-04 fix). |
| `scripts/__init__.py` | Package marker | ✓ VERIFIED | Present, empty. |
| `scripts/build_catalog.py` | CLI entrypoint: load/query/fetch/map/dedupe/write | ✓ VERIFIED | All specified symbols present (`load_config`, `build_overpass_query`, `fetch_overpass`, `derive_id`, `map_element_to_venue`, `round5`, `dedupe_venues`, `write_json_atomic`, `run`, `main`); wired end-to-end; live run today confirms functional pipeline with the CR-01 fix in place. |
| `tests/__init__.py` | Package marker | ✓ VERIFIED | Present, empty. |
| `tests/test_build_catalog.py` | Unit coverage for pure functions + dedup + run() | ✓ VERIFIED | 32 test methods (20 original + 12 added by the fix pass), all substantive; `python3 -m unittest tests.test_build_catalog -v` → 32/32 pass, re-run fresh during this verification. |
| `data/venues.json` | Generated venue catalog (gitignored) | ✓ VERIFIED (regenerated during verification) | Regenerated live via `python3 scripts/build_catalog.py` → 906 field-complete entries, mode `0644` (world-readable per WR-05 fix, confirmed on the actual live output file, not just the unit test). |
| `data/venues.raw.json` | Raw Overpass response snapshot (gitignored) | ✓ VERIFIED (regenerated during verification) | Non-empty, present after live re-run, mode `0644`. |
| `.gitignore` | Excludes generated artifacts, keeps source tracked | ✓ VERIFIED | Contains `data/venues.json`, `data/venues.raw.json`, `__pycache__/`, `*.pyc`; `git check-ignore -q` succeeds for both generated files; `config/catalog_build.json` and `scripts/build_catalog.py` remain tracked (not ignored). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scripts/build_catalog.py` | `config/catalog_build.json` | `load_config()` reads via `json.load` at script start | ✓ WIRED | Confirmed by code read and live run. |
| `scripts/build_catalog.py` | `https://overpass-api.de/api/interpreter` | `fetch_overpass()` POSTs via `urllib.request.urlopen` | ✓ WIRED | Confirmed by successful live run against the real endpoint today (930 elements fetched). |
| `scripts/build_catalog.py` | `data/venues.raw.json` | `run()` calls `write_json_atomic()` with the raw response | ✓ WIRED | File present and non-empty after live run; confirmed NOT written on the soft-failure path (CR-01 fix). |
| `scripts/build_catalog.py` | `data/venues.json` | `run()` calls `write_json_atomic()` with the mapped/deduped venues | ✓ WIRED | Wired and correct for success, empty-success, hard-failure, AND soft-failure paths — the previously-unwired soft-failure gap is now closed and independently reproduced as fixed. |
| `scripts/build_catalog.py::run()` | `scripts/build_catalog.py::dedupe_venues()` | called after `map_element_to_venue` filtering, before `write_json_atomic` on `CATALOG_PATH` | ✓ WIRED | `grep -n "dedupe_venues" scripts/build_catalog.py` shows both definition and call site; live run's "dropped (duplicate): 0" summary line confirms. |

### Prohibitions (must_haves.prohibitions, 01-01-PLAN.md)

| # | Statement | Verification Tier | Status | Evidence |
|---|-----------|-------------------|--------|----------|
| 1 | MUST NOT propagate OSM contributor/editor metadata (user/uid/changeset/contact:*) into data/venues.json | test | ✓ RESOLVED | `map_element_to_venue` returns exactly `{id, name, category, lat, lon}`; `test_map_element_whitelists_fields_only` passes. |
| 2 | MUST NOT construct an Overpass query broader than the configured bbox/allowlist (no wildcard amenity selector) | test | ✓ RESOLVED | `build_overpass_query` always builds `["amenity"~"^(...)$"]` from the config allowlist; `test_query_has_no_wildcard_amenity_filter` passes. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite passes offline | `python3 -m unittest tests.test_build_catalog -v` | 32/32 pass (was 20/20 pre-fix; 12 new regression tests added by the fix pass) | ✓ PASS |
| Live end-to-end build against real Overpass API | `python3 scripts/build_catalog.py --config config/catalog_build.json` | `Fetched: 930, dropped (missing field): 24, dropped (duplicate): 0, final catalog: 906`, exit 0 | ✓ PASS |
| Catalog shape (exactly 5 keys, all present) | programmatic check over live `data/venues.json` | shape ok: True, empty names: 0 | ✓ PASS |
| Category allowlist conformance | programmatic check over live `data/venues.json` | categories ⊆ allowed: True | ✓ PASS |
| Bbox conformance | programmatic check comparing every venue's lat/lon to config bbox | venues outside bbox: 0 | ✓ PASS |
| Dedup key collision check | programmatic check over live `data/venues.json` | dedup ok (no collisions): True | ✓ PASS |
| Output file permissions | `ls -la data/venues.json data/venues.raw.json` | `0644` (world-readable) on actual live output, confirming WR-05 fix applies outside the unit test too | ✓ PASS |
| No hardcoded bbox/amenity/scheduler code in script | `grep` for literal coordinate/amenity substrings and scheduler/loop/daemon patterns | zero hits for both | ✓ PASS |
| Gitignore correctness | `git check-ignore -q data/venues.json` / `data/venues.raw.json` (separately) | `IGNORED_OK`; `config/catalog_build.json` and `scripts/build_catalog.py` confirmed NOT ignored | ✓ PASS |
| **CR-01 fix independent reproduction** | Injected `fetch_fn` returning `{"version": 0.6, "remark": "runtime error: Query timed out"}` (no `elements` key) into `run()`, against a `catalog_path` pre-seeded with one existing venue — the exact scenario the prior verification used to prove the gap | `exit_code: 1`; catalog after run byte-identical to pre-seeded content; no raw snapshot written | ✓ PASS — gap confirmed closed |
| Fix commits exist and match 01-REVIEW-FIX.md's claims | `git log --oneline -- scripts/build_catalog.py tests/test_build_catalog.py`; `git cat-file -e <hash>` for each of f33af38, c393f95, 01d6b80, e123ad2, 22c669e, b4c77ef | All 6 commits present in history with matching messages | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| VENU-01 | 01-01 | Catalog includes only allowed amenity-tagged OSM places | ✓ SATISFIED | Truth #1, live run categories check |
| VENU-02 | 01-01 | Places missing name/lat/lon/amenity discarded | ✓ SATISFIED | Truth #2, unit tests + live drop count |
| VENU-03 | 01-01 | Coverage scoped to one bbox via config only, no code change | ✓ SATISFIED | Truth #1, grep for hardcoded values |
| VENU-04 | 01-02 | Duplicate dropped on same name + 5-decimal-rounded coords | ✓ SATISFIED | Truth #3, unit tests + live collision check |
| VENU-05 | 01-01 + 01-02 | Stable OSM-derived identifier per venue, survives dedup | ✓ SATISFIED | Truth #4, `test_dedupe_keeps_first_id_on_collision` |
| VENU-06 | 01-01 + 01-02 | Static snapshot, regenerated on demand only, distinguishing failure from empty success | ✓ SATISFIED | Truth #5 (on-demand-only) and truth #6 (failure/empty distinction, CR-01 fix independently reproduced) both satisfied |

No orphaned requirements: REQUIREMENTS.md's traceability table maps only VENU-01 through VENU-06 to Phase 1, and all 6 are claimed across the two plans' `requirements:` frontmatter with no unclaimed IDs.

Note: `.planning/REQUIREMENTS.md`'s Traceability table still shows "Gaps Found" for all six VENU rows and the checklist boxes are unchecked — this appears to be stale bookkeeping from before the fix pass rather than a code issue; it is not something this verification's evidence (fresh code + fresh test run + fresh live run) contradicts, but the table should be updated to "Verified"/checked to reflect this passed re-verification.

### Anti-Patterns Found

None blocking. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in `scripts/build_catalog.py` or `tests/test_build_catalog.py`. The previously-flagged blocker (silent `response.get("elements", [])` fallback) is resolved — replaced with an explicit `"elements" not in response` check that raises. The 5 previously-flagged warnings/info items (WR-01 unused allowlist param, WR-02 unstripped stored name, WR-03 narrow exception catch, WR-04 untyped config validation, WR-05 restrictive file permissions) are all resolved per code read and the reproductions above.

### Human Verification Required

None. All must-haves resolve programmatically; no behavior-dependent truths remain unverified.

## Gaps Summary

No gaps. This re-verification independently reproduced the exact soft-failure scenario the prior
verification used to demonstrate CR-01 (a valid-JSON Overpass response missing the `elements` key,
against a pre-seeded populated catalog) and confirmed it now correctly returns a non-zero exit code
and leaves the existing catalog byte-for-byte untouched — the fix is real, not just claimed. All 5
warning/info-level fixes from the same review-fix pass are also confirmed present and functioning
in the current code (verified against the live output file, not only unit tests, for WR-05). A
fresh live run against the real Overpass API today produced 906 field-complete, correctly-filtered,
duplicate-free, stably-identified venues, and all 6 roadmap-mapped requirements (VENU-01 through
VENU-06) are satisfied. Phase 1 goal is achieved: a real, deduplicated venue catalog for one city
bounding box exists for Phase 2 to ingest.

---

_Verified: 2026-09-20T11:30:00Z_
_Verifier: Claude (gsd-verifier)_
