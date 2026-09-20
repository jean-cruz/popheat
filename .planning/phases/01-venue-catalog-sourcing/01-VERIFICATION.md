---
phase: 01-venue-catalog-sourcing
verified: 2026-09-20T00:00:00Z
status: gaps_found
score: 5/6 must-haves verified
covered_files: [".gitignore", ".planning/REQUIREMENTS.md", ".planning/phases/01-venue-catalog-sourcing/01-01-PLAN.md", ".planning/phases/01-venue-catalog-sourcing/01-01-SUMMARY.md", ".planning/phases/01-venue-catalog-sourcing/01-02-PLAN.md", ".planning/phases/01-venue-catalog-sourcing/01-02-SUMMARY.md", ".planning/phases/01-venue-catalog-sourcing/01-REVIEW.md", "config/catalog_build.json", "scripts/__init__.py", "scripts/build_catalog.py", "tests/__init__.py", "tests/test_build_catalog.py"]
covered_digest: "v1:sha256:0cc05e2b35946c4e8076efc5e044bf04eb873539ff28f75c425dcd83c9dcc251"
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "A failed Overpass fetch leaves the existing data/venues.json catalog untouched, distinct from a genuine zero-match success (D-05 / VENU-06 failure-vs-empty-result distinction — must_haves truth in 01-02-PLAN.md, also documented as run()'s own guaranteed contract)"
    status: failed
    reason: >
      fetch_overpass()/run() only classify network errors, oversized responses, and
      genuinely-invalid JSON as failures. A syntactically valid HTTP 200 response whose body
      is well-formed JSON but omits the "elements" key entirely — the real, documented shape
      overpass-api.de returns on server-side timeout/rate-limit soft-failure, e.g.
      {"version": 0.6, "remark": "runtime error: Query timed out"} — is NOT detected as a
      failure. run() falls through to `elements = response.get("elements", [])`, gets an
      empty list, proceeds through dedupe, and calls write_json_atomic(catalog_path, [])
      unconditionally — silently replacing any existing, populated catalog with an empty one
      and exiting 0 with an ordinary-looking "final catalog: 0" summary line. This is
      indistinguishable from the outside from a genuine zero-match query, and directly
      contradicts (a) run()'s own docstring guarantee ("A failed fetch leaves whatever is
      already at catalog_path untouched"), and (b) 01-02-SUMMARY.md's coverage claim (id D2,
      requirement VENU-06, human_judgment: false) that this invariant was "mechanically
      proven" — the actual unit tests for this behavior
      (test_run_fetch_failure_leaves_existing_catalog_untouched_and_exits_nonzero) only cover
      a raised OverpassFetchError, and
      (test_run_empty_overpass_result_writes_empty_catalog_and_exits_zero) only covers a
      genuine {"elements": []} response — neither exercises the valid-JSON/missing-"elements"
      soft-failure case. This is not a hypothetical: it was flagged as Critical (CR-01) in
      01-REVIEW.md and independently reproduced during this verification (see Behavioral
      Spot-Checks below) — a fake fetch_fn returning {"remark": "runtime error: ..."} against
      a catalog_path pre-seeded with one existing venue produces exit code 0 and an emptied
      catalog file.
    artifacts:
      - path: "scripts/build_catalog.py"
        issue: "fetch_overpass (~lines 95-121) never validates that the parsed Overpass JSON response actually contains an \"elements\" key before returning it to the caller; run() (~lines 250-253) reads elements via response.get(\"elements\", []) which silently substitutes an empty list rather than distinguishing 'no elements key present' from 'elements key present and empty'."
    missing:
      - "In fetch_overpass (preferred) or immediately after the fetch_fn call in run(), raise OverpassFetchError when \"elements\" is not a key of the parsed response (optionally including response.get(\"remark\") in the error message) so this soft-failure mode is routed through the existing except OverpassFetchError path in run(), which already correctly preserves the current catalog_path/raw_path contents and exits non-zero."
      - "A regression test asserting that a fetch_fn returning {\"remark\": \"...\"} (no \"elements\" key) leaves a pre-seeded catalog_path untouched and returns a non-zero exit code, mirroring the existing test_run_fetch_failure_leaves_existing_catalog_untouched_and_exits_nonzero test but for this specific response shape."
---

# Phase 1: Venue Catalog Sourcing Verification Report

**Phase Goal:** A real, deduplicated venue catalog for one city bounding box exists for the pipeline to ingest
**Verified:** 2026-09-20
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Catalog build against OSM for the configured bbox yields only bar/pub/restaurant/cafe/fast_food/nightclub-tagged venues; changing the bbox is config-only | ✓ VERIFIED | `build_overpass_query` builds the regex/bbox exclusively from `config["amenity_allowlist"]`/`config["bounding_box"]`; `grep -n "41\.\|8\.6\|-8\."` and a literal-amenity-string grep against `scripts/build_catalog.py` both returned zero hits (no hardcoded coordinates or amenity strings). Live re-run against overpass-api.de today produced 906 venues; every entry's `category` is a member of `{bar,pub,restaurant,cafe,fast_food,nightclub}` and every entry's lat/lon falls within the configured bbox (verified programmatically, see Behavioral Spot-Checks). |
| 2 | Places missing name, latitude, longitude, or amenity tag are excluded from the catalog | ✓ VERIFIED | `map_element_to_venue` returns `None` for missing/empty/whitespace-only name, missing amenity, and missing lat/lon/center — covered by 5 passing unit tests (`test_map_element_drops_missing_name` w/ 3 subTests, `test_map_element_drops_missing_lat_lon`, `test_map_element_drops_missing_amenity`). Live run today: 24 of 930 fetched elements dropped for missing fields; 0 of the 906 surviving entries have an empty/whitespace-only name. |
| 3 | No two catalog entries share the same name and coordinates rounded to 5 decimal places | ✓ VERIFIED | `dedupe_venues` keyed on `(name, round5(lat), round5(lon))`, first-occurrence-wins, order-preserving; `round5` uses explicit `decimal.Decimal(...).quantize(..., ROUND_HALF_UP)`, never native float `round()`. 6 passing unit tests cover boundary rounding, empty/single input, case-sensitivity (no false merge), first-id-on-collision, and survivor-order preservation. Live run today: 906-entry `data/venues.json` has zero `(name, round(lat,5), round(lon,5))` key collisions (verified programmatically). |
| 4 | Every catalog venue carries a stable identifier derived from its OSM source record | ✓ VERIFIED | `derive_id(element)` returns `f"{element['type']}/{element['id']}"`; `test_derive_id_node_and_way` passes. Live catalog: all 906 `id` values are non-empty and contain a `/` separating OSM type from OSM numeric id (e.g. `node/1223740137`). |
| 5 | The catalog is produced by an on-demand build step, not recomputed automatically on every ingestion cycle | ✓ VERIFIED | `scripts/build_catalog.py` contains no scheduler, cron, daemon, polling loop, or file-watch code — `main()`/`run()` execute exactly once per `python3 scripts/build_catalog.py` invocation and return. This is a structural absence (no such code exists anywhere in the phase's files), consistent with 01-01-SUMMARY.md's own human-judgment rationale for this item. |
| 6 | A failed Overpass fetch leaves the existing catalog untouched, distinct from a genuine zero-match success (VENU-06 failure/empty distinction, PLAN 01-02 must-have + run()'s documented contract) | ✗ FAILED | See `gaps` in frontmatter and Gaps Summary below. A soft-failure Overpass response (valid JSON, no `elements` key — e.g. a `remark`-only timeout response) is treated as a genuine empty successful result and silently overwrites an existing populated catalog. Reproduced directly (see Behavioral Spot-Checks). |

**Score:** 5/6 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `config/catalog_build.json` | Bounding box, amenity allowlist, Overpass endpoint/timeouts/byte-cap (6 keys) | ✓ VERIFIED | All 6 required keys present with correct types/values; consumed by `load_config`. |
| `scripts/__init__.py` | Package marker | ✓ VERIFIED | Present, empty, makes `scripts` importable for tests. |
| `scripts/build_catalog.py` | CLI entrypoint: load/query/fetch/map/dedupe/write | ✓ VERIFIED (with 1 gap, see truth #6) | All specified symbols present (`load_config`, `build_overpass_query`, `fetch_overpass`, `derive_id`, `map_element_to_venue`, `round5`, `dedupe_venues`, `write_json_atomic`, `run`, `main`); wired end-to-end; live run today confirms functional pipeline. One correctness gap in fetch-failure detection (truth #6). |
| `tests/__init__.py` | Package marker | ✓ VERIFIED | Present, empty. |
| `tests/test_build_catalog.py` | Unit coverage for pure functions + dedup + run() | ✓ VERIFIED | 20 test methods across both plans, all substantive (real assertions, not stubs); `python3 -m unittest tests.test_build_catalog` → 20/20 pass, re-run during this verification. |
| `data/venues.json` | Generated venue catalog (gitignored) | ✓ VERIFIED (regenerated during verification) | Did not exist on disk at verification start (gitignored generated artifact, correctly absent from git); regenerated live via `python3 scripts/build_catalog.py` → 906 field-complete entries, confirmed present now for Phase 2 to consume. |
| `data/venues.raw.json` | Raw Overpass response snapshot (gitignored) | ✓ VERIFIED (regenerated during verification) | Same as above — non-empty, present after live re-run. |
| `.gitignore` | Excludes generated artifacts, keeps source tracked | ✓ VERIFIED | Contains `data/venues.json`, `data/venues.raw.json`, `__pycache__/`, `*.pyc`; `git check-ignore -q data/venues.json data/venues.raw.json` succeeds; `config/catalog_build.json` and `scripts/build_catalog.py` remain tracked (not ignored). |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `scripts/build_catalog.py` | `config/catalog_build.json` | `load_config()` reads via `json.load` at script start | ✓ WIRED | Confirmed by code read and live run (config values flow into query construction). |
| `scripts/build_catalog.py` | `https://overpass-api.de/api/interpreter` | `fetch_overpass()` POSTs via `urllib.request.urlopen` | ✓ WIRED | Confirmed by successful live run against the real endpoint during this verification (930 elements fetched). |
| `scripts/build_catalog.py` | `data/venues.raw.json` | `run()` calls `write_json_atomic()` with the raw response | ✓ WIRED | File present and non-empty after live run. |
| `scripts/build_catalog.py` | `data/venues.json` | `run()` calls `write_json_atomic()` with mapped/deduped venues | ✓ WIRED, ⚠️ with correctness gap | Wired and functional for the tested failure/success paths; NOT safe against the untested soft-failure path (truth #6 / CR-01). |
| `scripts/build_catalog.py::run()` | `scripts/build_catalog.py::dedupe_venues()` | called after `map_element_to_venue` filtering, before `write_json_atomic` on `CATALOG_PATH` | ✓ WIRED | `grep -n "dedupe_venues" scripts/build_catalog.py` shows both definition and call site; confirmed by live run's "dropped (duplicate): 0" summary line and code read. |

### Prohibitions (must_haves.prohibitions, 01-01-PLAN.md)

| # | Statement | Verification Tier | Status | Evidence |
|---|-----------|-------------------|--------|----------|
| 1 | MUST NOT propagate OSM contributor/editor metadata (user/uid/changeset/contact:*) into data/venues.json | test | ✓ RESOLVED | `map_element_to_venue` returns exactly `{id, name, category, lat, lon}`; `test_map_element_whitelists_fields_only` asserts this with a synthetic element carrying `user`/`uid`/`changeset`/`contact:phone` and passes. |
| 2 | MUST NOT construct an Overpass query broader than the configured bbox/allowlist (no wildcard amenity selector) | test | ✓ RESOLVED | `build_overpass_query` always builds `["amenity"~"^(...)$"]` from the config allowlist, never a bare `["amenity"]`; `test_query_has_no_wildcard_amenity_filter` passes. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full unit suite passes offline | `python3 -m unittest tests.test_build_catalog -v` | 20/20 pass | ✓ PASS |
| Live end-to-end build against real Overpass API | `python3 scripts/build_catalog.py --config config/catalog_build.json` | `Fetched: 930, dropped (missing field): 24, dropped (duplicate): 0, final catalog: 906`, exit 0 | ✓ PASS |
| Catalog shape (exactly 5 keys, all present) | `python3 -c "..."` shape check over `data/venues.json` | `exact 5 keys only: True`, `empty names: 0` | ✓ PASS |
| Category allowlist conformance | programmatic check over live `data/venues.json` | `categories present: {fast_food, bar, nightclub, pub, restaurant, cafe}` — subset of allowed | ✓ PASS |
| Bbox conformance | programmatic check comparing every venue's lat/lon to config bbox (small tolerance) | `venues outside bbox: 0` | ✓ PASS |
| Dedup key collision check | programmatic check over live `data/venues.json` | `dedup ok (no collisions): True` | ✓ PASS |
| No hardcoded bbox/amenity values in script | `grep` for literal coordinate/amenity substrings in `scripts/build_catalog.py` | zero hits | ✓ PASS |
| Gitignore correctness | `git check-ignore -q data/venues.json data/venues.raw.json` | `IGNORED_OK` | ✓ PASS |
| **Soft-failure overwrite reproduction (CR-01)** | Injected `fetch_fn` returning `{"remark": "runtime error: Query timed out"}` (no `elements` key) into `run()`, against a `catalog_path` pre-seeded with one existing venue | `exit_code: 0`; catalog after run: `[]` (existing venue silently destroyed) | ✗ FAIL — confirms 01-REVIEW.md's CR-01 finding is real and unresolved |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| VENU-01 | 01-01 | Catalog includes only allowed amenity-tagged OSM places | ✓ SATISFIED | Truth #1, live run categories check |
| VENU-02 | 01-01 | Places missing name/lat/lon/amenity discarded | ✓ SATISFIED | Truth #2, unit tests + live drop count |
| VENU-03 | 01-01 | Coverage scoped to one bbox via config only, no code change | ✓ SATISFIED | Truth #1, grep for hardcoded values |
| VENU-04 | 01-02 | Duplicate dropped on same name + 5-decimal-rounded coords | ✓ SATISFIED | Truth #3, unit tests + live collision check |
| VENU-05 | 01-01 + 01-02 | Stable OSM-derived identifier per venue, survives dedup | ✓ SATISFIED | Truth #4, `test_dedupe_keeps_first_id_on_collision` |
| VENU-06 | 01-01 + 01-02 | Static snapshot, regenerated on demand only | ⚠️ PARTIALLY SATISFIED | Truth #5 (on-demand-only) ✓ satisfied; the "distinct failure vs. empty-result" half of this requirement's contract (truth #6) is **not** satisfied — see gap. |

No orphaned requirements: REQUIREMENTS.md's traceability table maps only VENU-01 through VENU-06 to Phase 1, and all 6 are claimed across the two plans' `requirements:` frontmatter with no unclaimed IDs.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `scripts/build_catalog.py` | ~252-253 | Silent fallback (`response.get("elements", [])`) masking a distinguishable failure mode as success | 🛑 Blocker | Drives the FAILED truth #6 / gap above (CR-01) |
| `scripts/build_catalog.py` | 129/137-145 | `map_element_to_venue`'s `allowlist` parameter is accepted but never used — no local defense-in-depth amenity check, relies entirely on server-side Overpass filtering | ⚠️ Warning | Does not currently violate VENU-01 (server-side filter is correct and empirically verified today), but is a latent risk if the query-construction regex and this function ever diverge (01-REVIEW.md WR-01) |
| `scripts/build_catalog.py` | 138-162 | Venue `name` is validated stripped but stored unstripped, so incidental whitespace differences from OSM data entry can prevent an otherwise-true duplicate from being merged | ⚠️ Warning | Does not violate the literal VENU-04 wording (entries genuinely differ in stored name string) but reduces real-world dedup effectiveness (01-REVIEW.md WR-02) |
| `scripts/build_catalog.py` | 107-121 | `fetch_overpass` only catches `(urllib.error.URLError, socket.timeout)`; some lower-level I/O errors during `response.read()` could propagate as uncaught exceptions | ℹ️ Info | Would crash with a raw traceback instead of the intended `ERROR: ...`/exit-1 contract (01-REVIEW.md WR-03) |
| `scripts/build_catalog.py` | 47-75 | `load_config` validates key presence but not value types | ℹ️ Info | A malformed config (e.g. string instead of number) would raise an uncaught `TypeError` rather than `ConfigError` (01-REVIEW.md WR-04) |
| `scripts/build_catalog.py` | 195-213 | Atomic write leaves output files at `0600` permissions | ℹ️ Info | Could block Phase 2 pipeline read access if it runs under a different OS user (01-REVIEW.md WR-05) — likely moot for a same-user contest demo, but worth confirming during Phase 2 |

No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers found in any phase-modified file.

### Human Verification Required

None required to resolve the blocking gap (it is mechanically reproducible and mechanically fixable). One informational item, not currently blocking:

### 1. Catalog ordering stability across regeneration runs

**Test:** N/A — this is a `verification: backstop`-tagged must-have from 01-02-PLAN.md documenting a non-guarantee ("Catalog order across separate live-query regeneration runs is not contractually guaranteed to be stable, since the Overpass API does not guarantee response ordering across separate calls").
**Expected:** No code path should implicitly assume or depend on cross-run order stability.
**Why human:** This is a documented disclaimer rather than an assertable behavior; per verification policy, `backstop`-tagged items are not certified as VERIFIED on presence/absence of contradicting code alone — flagged here for awareness, not counted toward the score, and not blocking (overall status is already `gaps_found` for an unrelated, concrete reason).

## Gaps Summary

Phase 1 successfully delivers a real, live-sourced, deduplicated, config-scoped venue catalog: a
fresh run today against the live Overpass API produced 906 field-complete, correctly-filtered,
duplicate-free, stably-identified venues at `data/venues.json`, and every one of the 5 literal
roadmap success criteria is independently verified against the current codebase (not just trusted
from SUMMARY.md). Phase 2 has a real catalog file to ingest right now.

However, one concrete, previously-flagged-and-unresolved defect (CR-01 in `01-REVIEW.md`, Critical
severity) blocks a clean pass: `run()` cannot distinguish a genuine Overpass soft-failure (valid
HTTP 200 JSON body carrying a `remark` instead of `elements` — the documented shape
overpass-api.de returns under timeout/rate-limit, a realistic risk for a contest-day rebuild) from
a real zero-match success. On that failure mode, the script silently overwrites any existing
populated catalog with an empty one and exits 0 — directly contradicting the invariant `run()`'s
own docstring and 01-02-SUMMARY.md's coverage claims assert was "mechanically proven." This
verification independently reproduced the defect (see Behavioral Spot-Checks). The fix is small
and well-scoped (raise `OverpassFetchError` when `"elements"` is absent from the parsed response),
and the code review already proposes the exact patch — this is a closure-plan-sized gap, not a
phase-goal-sized one.

---

_Verified: 2026-09-20_
_Verifier: Claude (gsd-verifier)_
