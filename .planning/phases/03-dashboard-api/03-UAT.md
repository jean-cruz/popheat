---
status: testing
phase: 03-dashboard-api
source: [03-VERIFICATION.md]
started: 2026-09-21T18:05:00Z
updated: 2026-09-21T18:05:00Z
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

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
