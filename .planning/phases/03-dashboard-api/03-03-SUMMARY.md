---
phase: 03-dashboard-api
plan: 03
subsystem: ui
tags: [leaflet, fetch, polling, dashboard]
requires:
  - phase: 03-dashboard-api
    provides: heat layer, markers, counts/telemetry panels, status badge (Plan 03-02)
provides:
  - 10-second auto-refresh loop with in-flight concurrency guard
  - stale-data error banner with dismiss control, auto-clearing on recovery
  - empty-state ("No readings yet") for a successful zero-venue response
affects: [dashboard-api]
actuals:
  tokens: 3857
  tasks: 2
  commits: 2
  plan_head_before: a85f724
tech-stack:
  added: []
  patterns: ["independent per-endpoint fetch with AbortController timeout, never a shared Promise.all catch"]
key-files:
  created: []
  modified: [iris/PopHeat/www/dashboard.html]
key-decisions:
  - "Each of the four endpoint fetches uses its own AbortController timeout (FETCH_TIMEOUT_MS = 8000) so one wedged connection cannot hold the isRefreshing guard forever"
  - "recordFetchFailure never touches any DOM outside the banner itself; dismissBanner is idempotent and is also called automatically by refreshAll on any cycle where all four fetches succeed"
  - "Banner copy's em dash is built via String.fromCharCode(8212) (EM_DASH), matching the existing MIDDOT pattern, to keep the file pure ASCII under IRIS's ISO-8859-1 static-file Content-Type"
patterns-established:
  - "recordFetchFailure never touches any DOM outside the banner itself"
requirements-completed: [DASH-07]
coverage:
  - id: D1
    description: "10-second polling loop re-fetches and re-renders venues/counts/telemetry/status with an in-flight guard and empty-state handling"
    requirement: "DASH-07"
    verification:
      - kind: other
        ref: "grep -q 'REFRESH_INTERVAL_MS' iris/PopHeat/www/dashboard.html && grep -q 'setInterval' ... && grep -q 'function refreshAll' ... && grep -q 'isRefreshing' ... && grep -q 'No readings yet' ... (Task 1 automated verify)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Stale-data banner shows exact D-07 copy on fetch failure, is dismissible, and auto-clears on recovery"
    requirement: "DASH-07"
    verification:
      - kind: other
        ref: "grep -q 'Unable to refresh' iris/PopHeat/www/dashboard.html && grep -q 'function recordFetchFailure' ... && grep -q 'aria-label=\"Dismiss\"' ... && grep -q 'function dismissBanner' ... (Task 2 automated verify)"
        status: pass
    human_judgment: true
    rationale: "Requires visually observing container stop/restart and the live banner; no automated test asserts this."
duration: 20min
completed: 2026-09-21
status: complete
---

# Phase 03 Plan 03: Live 10-second auto-refresh with stale-data banner Summary

Dashboard now polls all four PopHeat REST endpoints every 10 seconds via a guarded `refreshAll()` loop and surfaces a dismissible, auto-clearing red banner with the exact D-07 copy on any fetch failure.

## Performance
- **Duration:** ~20min (this session; continued from a prior run interrupted by an API rate limit after Task 1's code was written but before it was committed)
- **Started:** 2026-09-21T19:20:00Z (approx, continuation)
- **Completed:** 2026-09-21T19:39:57Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- 10-second polling loop (`REFRESH_INTERVAL_MS = 10000`) with an `isRefreshing` in-flight guard, no full page reload
- Independent per-endpoint fetch/render (`fetchRegion` + `AbortController` timeout) so one failure never blanks the others
- Stale-data banner with exact D-07 copy ("Unable to refresh — showing last known data as of {time}."), dismissible via an `aria-label="Dismiss"` button with a 44x44px hit area, auto-clears on the next fully-successful cycle
- Empty-state handling ("No readings yet") for a successful zero-venue response, with base map tiles still rendering underneath

## Task Commits
1. **Task 1: 10-second polling loop with in-flight guard and empty/loading states** - `88e7ccd` (feat)
2. **Task 2: Stale-data error banner with dismiss control** - `72872e3` (feat)

**Plan metadata:** commit hash recorded after this SUMMARY is written (see below)

## Files Created/Modified
- `iris/PopHeat/www/dashboard.html` - refresh loop, in-flight guard, empty state, stale-data banner, dismiss control

## Decisions Made
- Each of the four endpoint fetches uses its own `AbortController` timeout (`FETCH_TIMEOUT_MS = 8000`), shorter than the 10s refresh interval, so a wedged connection cannot hold the `isRefreshing` guard forever
- `recordFetchFailure()` only ever mutates the banner's own DOM nodes; it never resets or re-renders venues/heat/counts/telemetry/status, so those regions stay exactly as last rendered underneath the banner
- `dismissBanner()` is called both from the dismiss button's click handler and automatically at the point in `refreshAll()` where all four fetches are confirmed successful, so a recovered connection clears a previously-shown banner without requiring the user to notice or click anything
- The banner's em dash character is built via `String.fromCharCode(8212)` (`EM_DASH`), following the file's existing `MIDDOT` pattern, because IRIS serves this static file with an ISO-8859-1 `Content-Type` header that overrides the page's own `<meta charset="UTF-8">` — a literal UTF-8 em dash byte sequence would render as mojibake

## Deviations from Plan
None - plan executed exactly as written for both tasks.

## Issues Encountered
The previous executor run for this plan was interrupted by an API rate limit after Task 1's code had been fully written into the working tree but before anything was committed and before Task 2 was started. This run re-verified Task 1's acceptance criteria against the untouched working-tree state (still passing), committed it as its own commit, then implemented, verified, and committed Task 2. No code was reverted or reworked; the interruption caused no rework, only a delay in committing.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
Phase 3 (Dashboard & API) is now fully implemented across all 3 plans. Human verification of the
live stale-data banner (stopping/restarting the IRIS container and watching the banner appear,
stay accurate, dismiss, and auto-clear on recovery) remains outstanding — this is tracked as
coverage item D2 above with `human_judgment: true`, and will be harvested by the phase verifier
per `workflow.human_verify_mode: end-of-phase` into a UAT item. No container was stopped or
started during this execution run.

---
*Phase: 03-dashboard-api*
*Completed: 2026-09-21*

## Self-Check: PASSED
- FOUND: iris/PopHeat/www/dashboard.html
- FOUND: .planning/phases/03-dashboard-api/03-03-SUMMARY.md
- FOUND: 88e7ccd (Task 1 commit)
- FOUND: 72872e3 (Task 2 commit)
