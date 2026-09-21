---
status: complete
phase: 03-dashboard-api
source: [03-VERIFICATION.md]
started: 2026-09-21T18:05:00Z
updated: 2026-09-21T19:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Stale-data banner appear/dismiss/auto-clear across a real container stop/restart
expected: Red banner appears with the exact D-07 copy and a correct interpolated "last known data as of" time; all previously-rendered data stays visibly unchanged underneath; the "×" (aria-label="Dismiss") control hides the banner; after restart, the banner auto-clears on the next successful cycle without a manual page reload.
result: pass

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
