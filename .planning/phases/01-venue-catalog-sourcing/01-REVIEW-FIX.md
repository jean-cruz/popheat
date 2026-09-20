---
phase: 01-venue-catalog-sourcing
fixed_at: 2026-09-20T00:00:00Z
review_path: .planning/phases/01-venue-catalog-sourcing/01-REVIEW.md
iteration: 1
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 01: Code Review Fix Report

**Fixed at:** 2026-09-20T00:00:00Z
**Source review:** .planning/phases/01-venue-catalog-sourcing/01-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 6 (fix_scope: critical_warning — CR-01 + WR-01..WR-05; IN-01..IN-03 excluded by scope)
- Fixed: 6
- Skipped: 0

## Fixed Issues

### CR-01: Overpass soft-failure (valid JSON, no `elements`) silently overwrites existing catalog with empty data

**Files modified:** `scripts/build_catalog.py`, `tests/test_build_catalog.py`
**Commit:** f33af38
**Applied fix:** In `run()`, immediately after `fetch_fn` returns, raise `OverpassFetchError` if `"elements"` is not a key of the response (rather than defaulting via `.get("elements", [])`). This routes the soft-failure through the existing `except OverpassFetchError` handler, which prints the clean `ERROR: ...` message, returns exit code 1, and — critically — never calls `write_json_atomic` for either the raw snapshot or the catalog, leaving any existing catalog untouched (VENU-06, D-05). Added a regression test (`test_run_missing_elements_key_treated_as_failure_not_zero_match`) simulating a `{"remark": "..."}` response and asserting a non-zero exit code, an untouched existing catalog file, and no raw snapshot written.

### WR-01: `map_element_to_venue`'s `allowlist` parameter is accepted but never used

**Files modified:** `scripts/build_catalog.py`, `tests/test_build_catalog.py`
**Commit:** c393f95
**Applied fix:** Added `category not in allowlist` to the existing category-missing check in `map_element_to_venue`, so elements are dropped locally if their amenity is not in the configured allowlist — defense-in-depth alongside the server-side Overpass regex. Updated the docstring to explain why this local check exists. Added `test_map_element_drops_out_of_allowlist_amenity`.

### WR-02: Venue name is validated for blankness but stored unstripped

**Files modified:** `scripts/build_catalog.py`, `tests/test_build_catalog.py`
**Commit:** 01d6b80
**Applied fix:** `name` is now reassigned to its stripped form (`name = str(name).strip()`) immediately after the None-check, before the blank-check and before it's placed in the returned venue record — so the stored value and the dedupe key are both normalized. Added `test_map_element_stores_stripped_name`.

### WR-03: `fetch_overpass` does not catch all I/O errors that can occur during `response.read()`

**Files modified:** `scripts/build_catalog.py`, `tests/test_build_catalog.py`
**Commit:** e123ad2
**Applied fix:** Broadened the `except` clause around the `urlopen`/`response.read()` block from `(urllib.error.URLError, socket.timeout)` to `(urllib.error.URLError, socket.timeout, OSError, http.client.HTTPException)`, covering `ConnectionResetError` (a plain `OSError` subclass) and `http.client.IncompleteRead` (an `http.client.HTTPException`, not an `OSError`/`URLError` subclass) as called out in the review. Added two regression tests mocking `urllib.request.urlopen` to raise each error type during `.read()` and asserting both are wrapped as `OverpassFetchError`.

### WR-04: `load_config` validates key presence but not value types

**Files modified:** `scripts/build_catalog.py`, `tests/test_build_catalog.py`
**Commit:** 22c669e
**Applied fix:** Added a `NUMERIC_CONFIG_KEYS` tuple and an `_is_number()` helper (explicitly excluding `bool`, which is an `int` subclass in Python) and used it to validate `request_timeout_seconds`, `overpass_timeout_seconds`, `max_response_bytes`, and all four bbox coordinate values are numeric. Also validates `amenity_allowlist` is a non-empty list of strings. Any mismatch raises `ConfigError` with a message naming the offending key and value, so malformed config surfaces as the module's standard `ERROR: .../exit-1` contract instead of an uncaught `TypeError` inside `urlopen()`. Added six regression tests covering non-numeric timeout, bool-as-timeout, non-list allowlist, empty allowlist, non-numeric bbox value, and a valid-config sanity check.

### WR-05: Atomic write leaves output files with restrictive `0600` permissions

**Files modified:** `scripts/build_catalog.py`, `tests/test_build_catalog.py`
**Commit:** b4c77ef
**Applied fix:** Added `os.chmod(tmp.name, 0o644)` in `write_json_atomic` right before `os.replace()`, so the final `data/venues.json` / `data/venues.raw.json` are world-readable regardless of the restrictive `0600` mode `tempfile.NamedTemporaryFile` applies by default. Added `test_write_json_atomic_output_is_world_readable` asserting the final file's mode bits are `0o644`.

## Skipped Issues

None — all in-scope findings (CR-01, WR-01–WR-05) were fixed. IN-01, IN-02, and IN-03 were out of `fix_scope: critical_warning` and were not attempted.

## Verification

- Ran `python3 -m unittest discover -s tests -v` after each individual fix and once more after all six fixes were applied together, inside the isolated review-fix worktree (`.claude/worktrees/rf-01-*`, branch `gsd-reviewfix/01-*`, fast-forwarded onto `main` after this report). All runs passed: 32/32 tests green (20 pre-existing + 12 new regression tests added by this fix pass, one per finding plus extras for WR-03/WR-04).
- Each fix was verified with Tier 1 (re-read modified section) and Tier 2 (`python3 -c "import ast; ast.parse(...)"` syntax check) before being committed; no rollbacks were needed.
- These are pure-logic/config-validation fixes with direct unit-test coverage for the exact failure mode each finding describes — none require additional human logic verification beyond the standard commit review.

---

_Fixed: 2026-09-20T00:00:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
