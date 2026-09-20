---
phase: 01-venue-catalog-sourcing
reviewed: 2026-09-20T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - config/catalog_build.json
  - scripts/__init__.py
  - scripts/build_catalog.py
  - tests/__init__.py
  - tests/test_build_catalog.py
  - .gitignore
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-09-20T00:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed the standalone `scripts/build_catalog.py` CLI, its config, tests, and
supporting package files. The core pipeline (load config → build Overpass
query → fetch → map/filter → dedupe → atomic write) is well structured, has
solid docstrings tying logic back to spec IDs (VENU-01..06, D-05, D-10,
D-12, D-13), and the atomic-write/failure-preserves-existing-catalog
behavior is correctly implemented for the failure paths it anticipates
(`ConfigError`, `OverpassFetchError`).

The most significant issue is that a very plausible Overpass API failure
mode — a `200 OK` response whose JSON body carries a `remark` (soft
error/timeout) instead of an `elements` list — is not distinguished from a
genuine zero-result query, and will silently overwrite an existing
populated catalog with an empty one. This directly undermines the
documented "a failed fetch leaves the existing catalog untouched"
guarantee. Several secondary robustness gaps exist around config type
validation, exception coverage in `fetch_overpass`, an unused parameter in
`map_element_to_venue` that suggests missing defense-in-depth filtering,
and unnormalized venue names. No hardcoded secrets, injection vectors, or
dangerous function usage were found; `.gitignore` correctly excludes
generated data files.

## Critical Issues

### CR-01: Overpass soft-failure (valid JSON, no `elements`) silently overwrites existing catalog with empty data

**File:** `scripts/build_catalog.py:252-253` (consumed at `scripts/build_catalog.py:267`)
**Issue:** `fetch_overpass` only raises `OverpassFetchError` for network errors, oversized responses, or genuinely invalid JSON (lines 107-121). It does not validate that the parsed JSON actually represents a successful query result. The public Overpass API can return HTTP 200 with a well-formed JSON body that carries a `remark` field instead of `elements` when the query times out or hits a runtime error server-side (a common occurrence on the shared `overpass-api.de` endpoint this config points to). In `run()`:
```python
elements = response.get("elements", [])
fetched_count = len(elements)
```
this soft-failure response is indistinguishable from a genuine zero-match query. The pipeline proceeds to `write_json_atomic(catalog_path, deduped_venues)` with `deduped_venues == []`, unconditionally overwriting any previously-built catalog — even though the docstring for `run()` explicitly promises "A failed fetch leaves whatever is already at catalog_path untouched" (line 227-228). This is a real data-loss path: a transient Overpass rate-limit/timeout during a demo-day rebuild silently wipes the live dashboard's data source instead of failing loudly.
**Fix:** Treat the absence of an `"elements"` key as a fetch failure distinct from an empty list:
```python
if "elements" not in response:
    raise OverpassFetchError(
        f"Overpass response missing 'elements' (remark: {response.get('remark', 'none')})"
    )
elements = response["elements"]
```
Raise this inside `fetch_overpass` (or immediately after the call in `run()`) so it goes through the existing `except OverpassFetchError` path and preserves the current catalog.

## Warnings

### WR-01: `map_element_to_venue`'s `allowlist` parameter is accepted but never used

**File:** `scripts/build_catalog.py:129, 137-145`
**Issue:** `map_element_to_venue(element, allowlist)` takes an `allowlist` argument (and tests explicitly pass `VALID_CONFIG["amenity_allowlist"]` to it), but the function body never references `allowlist` — the only amenity filtering happens server-side via the Overpass regex built in `build_overpass_query`. This means there is no local defense-in-depth check that `tags.get("amenity")` is actually one of the configured categories; any element the Overpass server returns is trusted verbatim (VENU-02 discards only missing amenity, not out-of-allowlist amenity). If the regex construction ever diverges from the allowlist (e.g. future edit to `build_overpass_query` without updating the regex, or an Overpass API quirk returning tag-adjacent elements), invalid categories would flow straight into the public catalog.
**Fix:** Either use the parameter to enforce the check locally:
```python
if category not in allowlist:
    return None
```
or remove the unused parameter and rely explicitly (with a comment) on the server-side filter to avoid the misleading signature.

### WR-02: Venue name is validated for blankness but stored unstripped

**File:** `scripts/build_catalog.py:138-162`
**Issue:** The validation strips before checking (`str(name).strip() == ""`), but the raw, unstripped `name` value is what gets written into the venue record (`"name": name` at line 158). A name like `"  Bar A "` passes validation but is persisted with its original whitespace, which (a) surfaces inconsistently in the dashboard/popups, and (b) makes the dedupe key in `dedupe_venues` (which uses the exact `name` string, line 187) fail to merge otherwise-identical venues that only differ by incidental whitespace from OSM data entry inconsistencies.
**Fix:** Store the normalized value:
```python
name = str(name).strip()
if name == "":
    return None
...
return {"id": ..., "name": name, ...}
```

### WR-03: `fetch_overpass` does not catch all I/O errors that can occur during `response.read()`

**File:** `scripts/build_catalog.py:107-121`
**Issue:** The `try`/`except` only catches `(urllib.error.URLError, socket.timeout)`. `urllib.error.HTTPError` is a `URLError` subclass so HTTP-level failures are covered, but lower-level I/O errors raised while draining the socket inside `response.read(max_bytes + 1)` — e.g. `ConnectionResetError`, `http.client.IncompleteRead`, or `ssl.SSLError` in some code paths — are plain `OSError`/exception subclasses that are not always wrapped as `URLError` by `http.client`. Such an error would propagate out of `fetch_overpass` uncaught, past the `except OverpassFetchError` handler in `run()`, crashing the script with a raw traceback instead of the clean `ERROR: ...` message + exit code 1 the rest of the module consistently provides.
**Fix:** Broaden the catch to cover the read phase, e.g. wrap the whole block in `except (urllib.error.URLError, OSError) as e:` (or explicitly catch `http.client.HTTPException` alongside), still raising `OverpassFetchError` from it.

### WR-04: `load_config` validates key presence but not value types

**File:** `scripts/build_catalog.py:47-75`
**Issue:** `load_config` confirms the six required keys and the four bbox keys exist, but never checks that `request_timeout_seconds` / `overpass_timeout_seconds` / `max_response_bytes` are numeric, that `amenity_allowlist` is a non-empty list of strings, or that bbox values are numbers. A config with e.g. `"request_timeout_seconds": "30"` passes `load_config` cleanly, then causes `urllib.request.urlopen(request, timeout=request_timeout)` to raise a `TypeError` that is not `ConfigError`/`OverpassFetchError` and therefore not caught anywhere in `run()` — an uncaught traceback instead of the documented `ERROR: ...` / exit-1 contract.
**Fix:** Add minimal type/shape validation in `load_config` (e.g. `isinstance(config["amenity_allowlist"], list) and config["amenity_allowlist"]`, `isinstance(config[k], (int, float))` for the numeric keys) and raise `ConfigError` with a clear message on mismatch.

### WR-05: Atomic write leaves output files with restrictive `0600` permissions

**File:** `scripts/build_catalog.py:195-213`
**Issue:** `write_json_atomic` uses `tempfile.NamedTemporaryFile(..., delete=False)`, which creates the temp file with mode `0600` (owner read/write only) regardless of the process umask. After `os.replace(tmp.name, path)`, `data/venues.json` and `data/venues.raw.json` inherit that `0600` mode rather than the umask-derived mode a normal `open()`/`write()` would produce. If the IRIS Interoperability Production (or any other consumer/dashboard process) reads this file under a different OS user/service account, it will get a permission-denied error rather than the intended world/group-readable catalog file.
**Fix:** After `os.replace`, explicitly set the desired mode, e.g. `os.chmod(path, 0o644)`, or use `tempfile.mkstemp` with an explicit mode instead of `NamedTemporaryFile`'s default.

## Info

### IN-01: No validation that `amenity_allowlist` is non-empty before building the query

**File:** `scripts/build_catalog.py:78-92`
**Issue:** If `amenity_allowlist` in config were ever an empty list, `build_overpass_query` builds `amenity_regex = "^()$"`, producing a query that is syntactically valid but structurally can never match anything. This fails silently as a "successful, zero-result" run per VENU-06 semantics rather than as a clear configuration error, making the misconfiguration hard to diagnose.
**Fix:** In `load_config`, reject an empty `amenity_allowlist` with a `ConfigError`.

### IN-02: `DEFAULT_CONFIG_PATH` is relative to the current working directory

**File:** `scripts/build_catalog.py:22, 277-278`
**Issue:** `DEFAULT_CONFIG_PATH = "config/catalog_build.json"` only resolves correctly when the script is invoked from the repository root. Running `python scripts/build_catalog.py` from any other directory without `--config` fails with a `ConfigError` that (correctly) reports the file as not found, but the CLI gives no hint that the issue is cwd-relative pathing.
**Fix:** Either resolve the default relative to the script's own location (`os.path.join(os.path.dirname(__file__), "..", "config", "catalog_build.json")`) or document the cwd requirement in `--help`.

### IN-03: Amenity allowlist values are interpolated into a regex without escaping

**File:** `scripts/build_catalog.py:85`
**Issue:** `"^(" + "|".join(allowlist) + ")$"` interpolates config-controlled strings directly into an Overpass QL regex without `re.escape`. Not exploitable today since the config is developer-controlled and current values (`bar`, `pub`, `restaurant`, `cafe`, `fast_food`, `nightclub`) contain no regex metacharacters, but a future allowlist entry containing `.`, `|`, `(`, etc. would silently change query semantics rather than erroring.
**Fix:** Build the alternation with escaped values: `"|".join(re.escape(a) for a in allowlist)`.

---

_Reviewed: 2026-09-20T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
