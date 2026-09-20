# Phase 2: IRIS Ingestion Pipeline — Scoring, Classification & Telemetry - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-20
**Phase:** 2-IRIS Ingestion Pipeline — Scoring, Classification & Telemetry
**Areas discussed:** Peak-hour curve shape & timezone, IRIS/Docker environment setup, Persistence schema, Threshold configuration mechanism

**Mode:** `--auto` — fully autonomous, no user prompts. Every option below was auto-selected as the recommended default and logged for audit; no AskUserQuestion calls were made.

---

## Peak-hour curve shape & timezone

| Option | Description | Selected |
|--------|-------------|----------|
| Gaussian-style falloff, ~2h half-width, Europe/Lisbon local time | Smooth bell curve per peak hour; "current time" evaluated in Porto's local timezone | ✓ |
| Linear/triangular falloff, UTC | Simpler math, but timing would be off by the UTC offset during a live Porto demo | |

**User's choice (auto-selected):** Gaussian-style falloff, ~2h half-width, Europe/Lisbon local time
**Notes:** `specs/popularity-model.spec` R2 names peak hours per category but leaves exact curve shape/width unspecified — this was Claude's call to make plan-time-concrete. Local time was chosen because the demo is judged live and should show plausible Porto-time peak/weekend behavior.

---

## IRIS/Docker environment setup

| Option | Description | Selected |
|--------|-------------|----------|
| Official `intersystems/iris-community` image + docker-compose, single namespace, auto-start production | Minimal setup risk for a one-day build; production starts automatically on `docker compose up` | ✓ |
| Custom Dockerfile extending IRIS base image | More control but adds build/maintenance surface with no clear benefit for this scope | |

**User's choice (auto-selected):** Official image + docker-compose, single namespace, auto-start production
**Notes:** Directly satisfies the roadmap's "resiliently and without manual intervention" goal — no manual "start production" step needed for the demo.

---

## Persistence schema

| Option | Description | Selected |
|--------|-------------|----------|
| Two IRIS Persistent (SQL-projected) classes: `PopHeat.Reading`, `PopHeat.BatchTelemetry`, insert-only | Straightforward SQL-queryable schema; "latest per venue" derived via grouped query, never an update-in-place | ✓ |
| Single combined table for readings + telemetry | Simpler at first glance, but mixes two different cardinalities (per-venue vs per-batch) and complicates the "latest 20 batches" query | |

**User's choice (auto-selected):** Two separate Persistent classes, insert-only
**Notes:** Insert-only directly satisfies INGE-07/R6 ("never overwritten"); avoiding a denormalized "latest" table avoids a dual-write correctness risk during a one-day build.

---

## Threshold configuration mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| JSON config file, re-read every batch cycle | Mirrors Phase 1's `config/catalog_build.json` pattern; edits take effect on the next 3-second tick, no restart/redeploy | ✓ |
| IRIS production settings (Management Portal) | More "IRIS-native" but adds Management Portal setup/learning overhead not needed for a solo one-day build | |

**User's choice (auto-selected):** JSON config file, re-read every cycle
**Notes:** Satisfies HEAT-03's "adjustable... without a code change or redeploy" literally, and keeps a consistent "how do I retune this system" story across Phase 1 and Phase 2.

---

## Claude's Discretion

- Exact Gaussian width/height numeric parameters per category beyond the ~2h half-width guideline.
- Internal PyProd component topology (Business Service/Process/Operation split) — architecture pattern, not a vision decision.
- Exact batch-failure isolation mechanism (try/catch scope, IRIS Event Log usage).
- Exact IRIS class/property names beyond what's named in CONTEXT.md D-06.

## Deferred Ideas

None — discussion stayed within phase scope.
