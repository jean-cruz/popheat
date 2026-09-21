---
phase: 03-dashboard-api
verified: 2026-09-21T18:00:00Z
status: passed
score: 12/13 must-haves verified
covered_files: [".planning/REQUIREMENTS.md", ".planning/phases/03-dashboard-api/03-01-PLAN.md", ".planning/phases/03-dashboard-api/03-01-SUMMARY.md", ".planning/phases/03-dashboard-api/03-02-PLAN.md", ".planning/phases/03-dashboard-api/03-02-SUMMARY.md", ".planning/phases/03-dashboard-api/03-03-PLAN.md", ".planning/phases/03-dashboard-api/03-03-SUMMARY.md", ".planning/phases/03-dashboard-api/03-CONTEXT.md", ".planning/phases/03-dashboard-api/03-REVIEW.md", ".planning/phases/03-dashboard-api/03-UI-REVIEW.md", ".planning/phases/03-dashboard-api/03-UI-SPEC.md", "docker/init-production.sh", "iris/PopHeat/API.cls", "iris/PopHeat/Reading.cls", "iris/PopHeat/www/dashboard.html"]
covered_digest: "v1:sha256:a25c978f1a6d20cd006d23ad7ac3dde73e0170b3e57ba2b444bbc086fb2780fe"
behavior_unverified: 1
overrides_applied: 0
behavior_unverified_items:

  - truth: "A fetch failure on any 10-second refresh cycle shows the exact D-07 stale-data banner, and the banner auto-clears on the next fully-successful cycle after the underlying connection recovers (DASH-07 live stop/restart behavior)"
    test: "Load the live dashboard, let one refresh cycle succeed, then stop the IRIS container (or otherwise break connectivity) and watch the open tab for 10-20 seconds"
    expected: "The red banner appears reading 'Unable to refresh — showing last known data as of {the real last-successful-fetch time}.', every previously-rendered venue/heat/counts/telemetry/status element stays visibly unchanged underneath it, the '×' dismiss control hides it, and restarting the container clears the banner automatically on the next successful 10-second cycle with no manual reload"
    why_human: "This is a state-transition/recovery invariant (banner shows on failure, stays accurate, dismisses, and self-clears on recovery) that only manifests against a real broken/restored connection over multiple 10s cycles. No automated test exists in this repo (no JS test framework; tests/ contains only Python unit tests for Phase 1/2), and no docker/IRIS container was reachable in this verification environment (`docker ps` -> permission denied) or in the prior UI-audit sandbox (03-UI-REVIEW.md's own note). 03-03-SUMMARY.md explicitly discloses this was never run this session, and its supporting D2 coverage item is marked human_judgment: true."
human_verification:

  - test: "Load the live dashboard, let one refresh cycle succeed, then stop the IRIS container and watch the open tab for 10-20 seconds; then restart the container and wait for the next cycle"
    expected: "Red banner appears with the exact D-07 copy and a correct interpolated 'last known data as of' time; all previously-rendered data stays visibly unchanged underneath; the '×' (aria-label=\"Dismiss\") control hides the banner; after restart, the banner auto-clears on the next successful cycle without a manual page reload"
    why_human: "State-transition/recovery behavior across real container stop/restart over multiple 10s polling cycles — cannot be observed via grep/static analysis, and this environment has no docker access to exercise it directly (harvested from 03-03-PLAN.md Task 2's <human-check> per workflow.human_verify_mode: end-of-phase, and explicitly flagged as outstanding in 03-03-SUMMARY.md and 03-UI-REVIEW.md)."
---

# Phase 3: Dashboard & API Verification Report

**Phase Goal:** A live, publicly viewable dashboard shows current venue crowdedness on a map, refreshed automatically, backed by a REST API over the persisted readings and telemetry
**Verified:** 2026-09-21T18:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /venues returns the single latest reading per venue (D-04, ObservedAt DESC / ID DESC tiebreak), ordered by VenueId asc, `[]` when zero readings (DASH-01) | ✓ VERIFIED | `iris/PopHeat/Reading.cls:42-51` `Query LatestPerVenue` uses `ROW_NUMBER() OVER (PARTITION BY VenueId ORDER BY ObservedAt DESC, ID DESC) ... WHERE RowNum=1 ORDER BY VenueId ASC`; `API.cls:23-50` `Venues()` builds a `%DynamicArray` that stays empty (`[]`) when the result set has zero rows, never an error. Corroborated by 03-01-SUMMARY.md's live curl (906 objects, correct keys) and independently re-derived in 03-02-SUMMARY.md's SQL cross-check |
| 2 | GET /counts always emits all four heat-level keys (BAIXO/MEDIO/ALTO/CRITICO) as integers, computed from the identical latest-per-venue rule as /venues (DASH-05, D-04) | ✓ VERIFIED | `API.cls:57-79` `Counts()` pre-seeds all four keys to 0 before overwriting from the result set; `Reading.cls:59-68` `CountsByHeatLevel` is built on the textually identical RowNum=1 subquery `LatestPerVenue` uses. Live cross-check in 03-02-SUMMARY.md: a direct SQL `ROW_NUMBER()` query (ALTO 518/BAIXO 336/MEDIO 52) matched `/counts`'s `{"BAIXO":336,"MEDIO":52,"ALTO":518,"CRITICO":0}` exactly and summed to the same 906 as `/venues` |
| 3 | No time-window/staleness cutoff drops an old-but-still-latest reading | ✓ VERIFIED | Both `Query` definitions in `Reading.cls` filter only on `RowNum=1`; no `WHERE ObservedAt > ...` or similar time predicate exists anywhere in either query or in `API.cls` |
| 4 | GET /telemetry returns the same most-recent-batches data as `RecentBatches()`, newest first, capped at 20 | ✓ VERIFIED | `API.cls:84-107` `Telemetry()` delegates directly to `##class(%ResultSet).%New("PopHeat.BatchTelemetry:RecentBatches")`; `BatchTelemetry.cls:24-28` caps with `SELECT TOP 20 ... ORDER BY RecordedAt DESC` |
| 5 | GET /status returns `{"running": true\|false}` and never surfaces a raw error even if `IsProductionRunning` throws | ✓ VERIFIED | `API.cls:115-132` `Status()` wraps the call in its own Try/Catch, defaults `running=0` before the call, degrades to 0 on any exception, always writes HTTP 200 with a boolean `running` key |
| 6 | /status's outcome is independent of /venues, /counts, /telemetry (backstop) | ✓ VERIFIED | `Status()` shares no state, connection, or error path with the other three classmethods — each is an independent Try/Catch block. Directly observed live per 03-01-SUMMARY.md D4: stopping the production flipped `/status` to `{"running":false}` at HTTP 200 while `/venues`, `/counts`, `/telemetry` kept serving 200 |
| 7 | Heat layer renders one weighted point per venue (with a reading), floored at `Math.max(popularity, 0.15)`, no extra client-side rounding, insertion-order independent (DASH-02) | ✓ VERIFIED | `dashboard.html:505-527` `renderHeatLayer` builds `[lat, lon, Math.max(venue.popularity, MIN_HEAT_WEIGHT)]` per venue with `MIN_HEAT_WEIGHT=0.15`; no rounding applied. Leaflet.heat sums intensities regardless of array order (library behavior, not custom code) |
| 8 | Only ALTO/CRITICO venues get individual markers, CRITICO radius (14) strictly larger than ALTO (10), additive to (not instead of) the heat layer; BAIXO/MEDIO stay heat-layer-only (DASH-03, DASH-04) | ✓ VERIFIED | `dashboard.html:533-550` `renderMarkers` filters to `heatLevel === 'ALTO' || 'CRITICO'` only, sets `radius: CRITICO_RADIUS (14) : ALTO_RADIUS (10)`; called alongside (not instead of) `renderHeatLayer` from the same `renderVenues` entry point (line 632-633) |
| 9 | Marker popups wrap long venue names within a 240px max-width area instead of truncating | ✓ VERIFIED | `dashboard.html:321` `.popup-content { max-width: 240px; }`, no `text-overflow: ellipsis` or `white-space: nowrap` anywhere in the popup CSS. Confirmed rendered live in 03-02-SUMMARY.md with the longest real venue name wrapping onto two lines |
| 10 | Status badge shows "Pipeline: Running"/"Pipeline: Stopped" without ever gating or hiding venue/heat/counts/telemetry data (DASH-06) | ✓ VERIFIED | `dashboard.html:572-579` `renderStatus` touches only `#status-dot`/`#status-label` DOM nodes; structurally cannot affect other regions. Live-observed in 03-01/03-02 SUMMARYs: stopping `PopHeat.Production` flipped the badge while map/counts/telemetry kept showing last-persisted data unchanged |
| 11 | Counts panel renders four rows in Display/Label type, digit colored per heat level; telemetry panel renders newest batch's fields from `/telemetry[0]` | ✓ VERIFIED | `dashboard.html:583-607` `renderCounts`/`renderTelemetry`; CSS `.count-value` (28px/600) and `.count-label` (13px/600) match 03-UI-SPEC.md's Display/Label roles; `renderTelemetry` early-returns on an empty array rather than dereferencing `batches[0]` |
| 12 | Venues/counts/telemetry/status are all re-fetched and re-rendered every 10 seconds (`REFRESH_INTERVAL_MS=10000`) with no full page reload, guarded against overlapping in-flight cycles, and one endpoint's failure never blocks the other three (DASH-07) | ✓ VERIFIED | `dashboard.html:423,435,691-715` — `REFRESH_INTERVAL_MS=10000`, `isRefreshing` guard returns immediately on re-entry, four independent `fetchRegion()` calls each with their own try/catch-equivalent `.then/.catch`, no `location.reload()` anywhere in the file (`grep -c location.reload` → 0) |
| 13 | A fetch failure shows the exact D-07 banner copy without disturbing other regions, is dismissible, and auto-clears once the connection recovers (DASH-07) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Code is present and correctly wired: `recordFetchFailure()` (dashboard.html:641-649) only touches the banner's own DOM; banner copy matches D-07 exactly (`'Unable to refresh ' + EM_DASH + ' showing last known data as of ' + asOf + '.'`); `dismissBanner()` wired to the `×` button (`aria-label="Dismiss"`, 44×44px hit area) and auto-called on an all-four-succeed cycle. But this is a runtime recovery/state-transition invariant, and no automated test exercises it — 03-03-SUMMARY.md explicitly states "No container was stopped or started during this execution run," this verification environment also has no docker access, and 03-UI-REVIEW.md independently flags this exact gap as its #1 priority finding. Presence + wiring is not sufficient evidence for a state transition; see Human Verification |

**Score:** 12/13 truths verified (1 present, behavior-unverified)

### Prohibitions (Judgment-Tier, Non-Authoritative)

03-02-PLAN.md declares three `must_haves.prohibitions` with no explicit `verification` tier — treated as judgment-tier per ADR-550. LLM-judge assessment below is non-authoritative; human review recommended.

| # | Prohibition | Judgment | Evidence |
|---|-------------|----------|----------|
| 1 | MUST NOT present heat-level/popularity data as real, live-measured crowd data (DASH-02) | Not violated (LLM judgment) | `dashboard.html:333` top-bar subtitle "Synthetic crowdedness estimates · not measured crowd counts"; popup note (line 562) "Estimated crowdedness, not a safety warning." |
| 2 | MUST NOT let CRITICO/ALTO coloring/sizing imply an actual safety/danger emergency (DASH-04) | Not violated (LLM judgment) | Same popup note as above is the only textual framing near heat-colored markers; no "danger," "emergency," or "warning" language beyond the disclaimer itself |
| 3 | MUST NOT let the status badge be confused with a venue's own open/closed status (DASH-06) | Not violated (LLM judgment) | `dashboard.html:338-339` badge `title` attribute: "Status of the PopHeat ingestion pipeline — not any venue's opening hours"; label text itself says "Pipeline: Running/Stopped," never a venue name |

**unverified-prohibition — human review recommended**: all three are judgment-tier and were not independently confirmed by a human reviewer; flagged per policy, not blocking.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `iris/PopHeat/API.cls` | `%CSP.REST` dispatch class, GET /venues, /counts, /telemetry, /status | ✓ VERIFIED | Exists, extends `%CSP.REST`, `XData UrlMap` declares all 4 routes, all 4 classmethods implemented with Try/Catch/500 pattern; no INSERT/UPDATE/DELETE keyword anywhere (`grep -Ei 'insert |update |delete '` → 0 matches) |
| `iris/PopHeat/Reading.cls` | `LatestPerVenue` + `CountsByHeatLevel` queries, D-04 single source of truth | ✓ VERIFIED | Both queries present, built on the textually identical RowNum=1 subquery |
| `iris/PopHeat/www/dashboard.html` | Full visual contract: heat layer, ALTO/CRITICO markers, panels, badge, polling, banner, empty state | ✓ VERIFIED | 744 lines; all constants/functions from all 3 plans present and correctly implemented |
| `docker/init-production.sh` | Registers `/csp/popheat/api` and `/csp/popheat` web apps, both `AutheEnabled=64`, idempotent | ✓ VERIFIED | Both Modify-or-Create blocks present with `DispatchClass=PopHeat.API` / `Path=.../www/`, `AutheEnabled=64`, `MatchRoles=":<db resource>"`; every conditional kept on one physical line per the documented `<SYNTAX>` fix |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `dashboard.html` | `API.cls` | `fetch(API_BASE + '/venues')` | ✓ WIRED | `API_BASE = '/csp/popheat/api'`, `fetchRegion('/venues', renderVenues)` |
| `dashboard.html` | `API.cls` | `fetch(...counts\|telemetry\|status)` | ✓ WIRED | Three more `fetchRegion(...)` calls, one per endpoint, in `refreshAll()` |
| `dashboard.html` | `API.cls` | `setInterval(refreshAll, REFRESH_INTERVAL_MS)` | ✓ WIRED | `dashboard.html:738-739` |
| `API.cls` | `Reading.cls` | `PopHeat.Reading:LatestPerVenue` / `:CountsByHeatLevel` | ✓ WIRED | `%ResultSet.%New(...)` calls in `Venues()`/`Counts()` |
| `API.cls` | `BatchTelemetry.cls` | `PopHeat.BatchTelemetry:RecentBatches` | ✓ WIRED | `%ResultSet.%New(...)` call in `Telemetry()` |
| `docker/init-production.sh` | `API.cls` | `DispatchClass="PopHeat.API"` | ✓ WIRED | Present in the `/csp/popheat/api` registration block |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `dashboard.html` heat layer/markers | `venues[]` | `GET /venues` → `PopHeat.Reading:LatestPerVenue` → `PopHeat.Reading` table | Yes | ✓ FLOWING |
| `dashboard.html` counts panel | `counts{}` | `GET /counts` → `PopHeat.Reading:CountsByHeatLevel` → same table | Yes | ✓ FLOWING |
| `dashboard.html` telemetry panel | `batches[]` | `GET /telemetry` → `PopHeat.BatchTelemetry:RecentBatches` → `PopHeat.BatchTelemetry` table | Yes | ✓ FLOWING |
| `dashboard.html` status badge | `status.running` | `GET /status` → `Ens.Director.IsProductionRunning` | Yes | ✓ FLOWING |

No static fallbacks, hardcoded empty arrays feeding rendered output, or mock data paths found — every panel's data source traces to a live query.

### Behavioral Spot-Checks

SKIPPED (no runnable entry points in this verification environment). `docker ps` returns "permission denied" in this sandbox and no dev server is reachable, matching the same constraint already documented in 03-UI-REVIEW.md's own audit. Static/structural verification (Steps 3-6 above) was performed against the full source instead, and prior live evidence from the execution sessions (03-01/03-02-SUMMARY.md: live curl output, DOM computed-style assertions, a live SQL cross-check, and an actual `iop --stop`/restart of the production) was cross-referenced as corroborating evidence rather than accepted at face value.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| DASH-01 | 03-01 | Latest reading per venue only | ✓ SATISFIED | Truth #1 |
| DASH-02 | 03-02 | Heat map weighted, min visible weight | ✓ SATISFIED | Truth #7 |
| DASH-03 | 03-02 | ALTO/CRITICO-only markers | ✓ SATISFIED | Truth #8 |
| DASH-04 | 03-02 | CRITICO marker larger than ALTO | ✓ SATISFIED | Truth #8 |
| DASH-05 | 03-01 | Counts match latest-reading rule | ✓ SATISFIED | Truth #2 |
| DASH-06 | 03-01, 03-02 | Pipeline status shown, non-gating | ✓ SATISFIED | Truths #5, #6, #10 |
| DASH-07 | 03-03 | 10s auto-refresh, visible error state | ✓ SATISFIED (polling) / ⚠️ behavior-unverified (banner recovery) | Truths #12 (verified), #13 (present, behavior-unverified) |

All 7 requirement IDs declared across the three PLAN frontmatters (DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07) are accounted for — no orphaned requirements.

**Documentation staleness note (non-blocking):** `.planning/REQUIREMENTS.md`'s checklist still shows DASH-02, DASH-03, DASH-04, and DASH-06 as unchecked `[ ]` and its Traceability table lists them as "Pending," even though 03-02-SUMMARY.md's `requirements-completed` frontmatter and the code evidence above show them satisfied. This is a bookkeeping gap in REQUIREMENTS.md, not a functional gap in the implementation — flagged for correction at ship time, not treated as a verification failure.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER markers found in any of the 4 phase-modified files | — | none |

No debt markers, no stub returns (`return null`/`return {}`/`return []` feeding rendered output), no hardcoded-empty data paths that survive a successful fetch. Six warning-level and four info-level findings from the independent 03-REVIEW.md code review (e.g. `iop --start` failure masking, unpinned pip deps, hard CDN dependency with no local fallback, duplicated subquery text with no drift-prevention mechanism, missing API charset pin, no schema-level range/enum constraints) are pre-existing, disclosed, non-blocking robustness/defense-in-depth items — none prevents the phase goal from being achieved today, and none is a stub or fabricated-data pattern. They are not repeated here as gaps since they were already surfaced and are not must-have failures per the phase's own success criteria.

### Human Verification Required

#### 1. Stale-data banner live recovery cycle (DASH-07)

**Test:** With the container running, load `http://localhost:52773/csp/popheat/dashboard.html` and let one refresh cycle succeed. Run `docker compose stop iris` and watch the open tab for 10-20 seconds. Click the "×" dismiss control. Then run `docker compose start iris` and wait for the next 10-second cycle.
**Expected:** The red banner appears reading "Unable to refresh — showing last known data as of {a real time matching the last successful load}." with every previously-rendered venue/heat/counts/telemetry/status element unchanged underneath it; clicking "×" hides the banner; after restart, the banner clears automatically on the next successful cycle with no manual reload.
**Why human:** State-transition/recovery invariant across real connectivity loss and restore, spanning multiple 10-second polling cycles — cannot be observed via source inspection alone, no automated test exists in this repo for it, and this verification session has no docker access to exercise it directly. This is the exact check specified in 03-03-PLAN.md Task 2's own `<human-check>` block, explicitly disclosed as not-yet-run in 03-03-SUMMARY.md and flagged as the #1 priority item in 03-UI-REVIEW.md.

### Gaps Summary

No FAILED truths, no missing/stub artifacts, no broken key links. The phase goal (live, auto-refreshing dashboard backed by a REST API) is substantively achieved and code-verified across all 7 DASH requirements. The one open item is not a code defect but an unexercised runtime invariant: the D-07 stale-data banner's appear/dismiss/auto-clear cycle against a real container stop and restart has never actually been watched running, by this session or the prior execution/UI-audit sessions (all three independently note the same docker-access constraint). This routes the phase to `human_needed` rather than `passed` — one human pass through the container-stop/restart check would close it out.
