# Phase 2: IRIS Ingestion Pipeline — Scoring, Classification & Telemetry - Context

**Gathered:** 2026-09-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Stand up an IRIS Interoperability Production (embedded Python / PyProd) that continuously reads the static venue catalog from Phase 1 (`data/venues.json`), walks it in fixed-size batches on a timer, computes a synthetic popularity score per venue, classifies each reading into a heat-level label, persists every reading as a new row, and records one telemetry record per batch — resiliently and without manual intervention once running. No dashboard, no API, no popularity-visualization happens in this phase; this phase's sole output is a growing, queryable table of readings + telemetry that Phase 3 will read from.

</domain>

<decisions>
## Implementation Decisions

### Timing & Locale
- **D-01:** Peak-hour curves use a Gaussian-style falloff shape with roughly a 2-hour half-width around each category's stated peak hour(s) — `specs/popularity-model.spec` R2 names peak hours per category but leaves exact shape/width unspecified; this is Claude's/researcher's discretion to pin a concrete formula in the plan.
- **D-02:** "Current time" for peak-hour distance (R3) and the Friday–Sunday weekend boost (R4) is evaluated in Europe/Lisbon local time, not UTC — venues are physically in Porto, and a live demo watched by judges should show plausible local peak/weekend behavior rather than being off by the UTC offset.

### IRIS / Docker Environment
- **D-03:** IRIS runs via the official `intersystems/iris-community` Docker image, brought up with a single `docker-compose.yml` — no custom base image build. — **Reversibility:** reversible — swapping images/compose config later is a config-only change.
- **D-04:** A single IRIS namespace (e.g. `POPHEAT`) hosts the Interoperability Production; no multi-namespace split.
- **D-05:** The Interoperability Production auto-starts when the IRIS container starts (via IRIS auto-start production configuration), so "resiliently and without manual intervention" (roadmap goal) holds immediately after `docker compose up` — no manual "start production" step required for the demo.

### Persistence Schema
- **D-06:** Readings and telemetry are stored as two separate IRIS Persistent classes with SQL projection (queryable via embedded SQL / ODBC / REST in Phase 3): `PopHeat.Reading` (venue id, name, category, lat, lon, popularity, heat_level, observed_at) and `PopHeat.BatchTelemetry` (reading_count, elapsed_seconds, throughput, recorded_at).
- **D-07:** `PopHeat.Reading` is insert-only per R6/INGE-07 — there is no separate "latest reading" table; Phase 3 derives "latest per venue" via a grouped `MAX(observed_at)` query. — **Reversibility:** costly — introducing a denormalized "latest" table later would require a backfill and a dual-write migration if query performance at Phase 3 demands it.
- **D-08:** `observed_at` is indexed (or the class's default IDKEY/time-ordered storage is relied on) so "most recent 20 batches" (TELE-05) and "latest reading per venue" queries stay cheap at the catalog's actual size (906 venues / ~6 batches per full cycle).

### Threshold Configuration (HEAT-03/HEAT-04)
- **D-09:** Heat-level thresholds live in a JSON config file (mirroring Phase 1's `config/catalog_build.json` pattern), not in IRIS production settings or a database table — kept simple for a solo one-day build.
- **D-10:** The config file is re-read at the start of every batch cycle (not cached for the lifetime of the process), so editing a threshold takes effect on the next 3-second tick with no restart and no redeploy — directly satisfying HEAT-03's "adjustable... without a code change or redeploy."

### Claude's Discretion
- Exact Gaussian width/height numeric parameters per category beyond the ~2h half-width guideline (D-01) — pin concrete values during planning/research.
- Internal PyProd component topology (how many Business Service / Process / Operation stages; where scoring vs. classification vs. persistence logically live) — this is an IRIS architecture pattern, not a user-vision decision.
- Exact batch-failure isolation mechanism (INGE-05 / R4 ingestion-pipeline.spec) — e.g. try/catch scope, IRIS Event Log usage — implementation detail for planning.
- Exact IRIS class/property names beyond what's named in D-06 (schema field names may be refined during planning to match IRIS/PyProd conventions).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline & Domain Rules
- `specs/ingestion-pipeline.spec` — Authoritative batching/cadence/atomicity/failure-isolation rules (R1-R6).
- `specs/popularity-model.spec` — Score range, category curves, midnight wrap, weekend boost, randomness, no-caching rules (R1-R6).
- `specs/heat-classification.spec` — Nightlife vs. daytime thresholds, evaluation order, config-not-code requirement, BAIXO default (R1-R5).
- `specs/telemetry.spec` — Per-batch metric record, required fields, throughput derivation, non-blocking, 20-batch recent view (R1-R5).

### Upstream Input Contract (Phase 1)
- `data/venues.json` — The static venue catalog this phase reads from. Current live shape: `{"id": "node/1223740137", "name": "Hard Club", "category": "nightclub", "lat": 41.14, "lon": -8.61}`, 906 venues currently on disk. Regenerated on-demand by `scripts/build_catalog.py` — Phase 2 must not assume it changes mid-run.
- `.planning/phases/01-venue-catalog-sourcing/01-CONTEXT.md` — Phase 1's decisions (bbox, dedup, field shape) for continuity.

### Project-Level
- `.planning/PROJECT.md` — Core value, IRIS/PyProd constraint, synthetic-popularity compliance constraint.
- `.planning/REQUIREMENTS.md` — INGE-01 through INGE-07, POPU-01 through POPU-06, HEAT-01 through HEAT-04, TELE-01 through TELE-05, the requirements this phase covers.

</canonical_refs>

<code_context>
## Existing Code Insights

Repository has one prior phase's output: `scripts/build_catalog.py` (Phase 1's venue catalog builder) and its config pattern at `config/catalog_build.json`. No IRIS code, no Docker setup, and no persistence layer exist yet — this phase is greenfield for IRIS/PyProd work.

### Reusable Assets
- `config/catalog_build.json` pattern: a flat, developer-editable JSON config loaded at run/cycle start — reuse this same shape for the heat-threshold config (D-09/D-10) for consistency.

### Established Patterns
- Phase 1 validated config-driven behavior (bbox/allowlist as config, not hardcoded) — Phase 2 should extend this same discipline to heat-level thresholds per HEAT-03.

### Integration Points
- `data/venues.json` (Phase 1's output) is the sole input this phase reads.
- `PopHeat.Reading` / `PopHeat.BatchTelemetry` (this phase's output, per D-06) are the sole tables Phase 3's dashboard/API will read from.

</code_context>

<specifics>
## Specific Ideas

- Timezone choice (D-02, Europe/Lisbon) is specifically because this is a live Porto demo for contest judges — the "current heat" story only reads as plausible if peak/weekend timing lines up with actual local time during the demo window.
- Config-file pattern for thresholds (D-09) deliberately mirrors Phase 1's `config/catalog_build.json` so the project has one consistent "how do I retune this system" story across both pipeline phases.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-IRIS Ingestion Pipeline — Scoring, Classification & Telemetry*
*Context gathered: 2026-09-20*
