---
status: testing
phase: 03-dashboard-api
source: [03-VERIFICATION.md]
started: 2026-09-21T18:05:00Z
updated: 2026-09-21T22:30:00Z
---

## Current Test

number: 1
name: Stale-data banner appear/dismiss/auto-clear across a real container stop/restart
expected: |
  Load the live dashboard, let one refresh cycle succeed, then stop the IRIS container and watch
  the open tab for 10-20 seconds; then restart the container and wait for the next cycle.
  Expected: Red banner appears with the exact D-07 copy and a correct interpolated "last known
  data as of" time; all previously-rendered data stays visibly unchanged underneath; the "×"
  (aria-label="Dismiss") control hides the banner; after restart, the banner auto-clears on the
  next successful cycle without a manual page reload.
awaiting: user response

## Tests

### 1. Stale-data banner appear/dismiss/auto-clear across a real container stop/restart
expected: Red banner appears with the exact D-07 copy and a correct interpolated "last known data as of" time; all previously-rendered data stays visibly unchanged underneath; the "×" (aria-label="Dismiss") control hides the banner; after restart, the banner auto-clears on the next successful cycle without a manual page reload.
result: [pending]
note: |
  Reopened 2026-09-21T22:30:00Z. The original "pass" was recorded against a container bind-mounted
  to a stale, orphaned git worktree (.claude/worktrees/agent-aaa532d2498e69de8, commit 699ad83,
  predating the 03-03 stale-banner feature entirely) whose dashboard.html had an empty stub
  `recordFetchFailure(){}`. Whatever the user observed, it could not have been the real banner
  logic. Container has since been recreated bind-mounted to the correct main checkout and
  re-initialized via docker/init-production.sh; confirmed live that the served dashboard.html now
  has the real recordFetchFailure() implementation and fitBounds map view. Retest needed.

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
