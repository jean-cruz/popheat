# PopHeat

## What This Is

PopHeat is a live heat map showing how crowded bars, restaurants, cafés, and other nightlife/food venues currently are. It's built as an InterSystems IRIS Interoperability Production (PyProd) that ingests a venue catalog sourced from OpenStreetMap, computes a synthetic popularity score per venue, classifies each reading into a business-facing crowdedness label, and serves a live-updating dashboard. It's being built as a solo entry for the InterSystems Portugal 2026 Programming Contest.

## Core Value

A working, submittable IRIS PyProd application, live and functioning end-to-end (ingest → score → classify → persist → dashboard), by the contest deadline. If the demo isn't running and the submission isn't in, nothing else about the project matters.

## Requirements

### Validated

- ✓ Venue catalog sourced from OpenStreetMap for one city bounding box, with eligibility/dedup rules applied — Phase 1
- ✓ IRIS Interoperability Production (PyProd) implementing the ingestion pipeline: batching, full-catalog cycling, batch atomicity, and failure isolation — Phase 2
- ✓ Popularity model computing a synthetic crowdedness score per venue, per category-specific daily curve — Phase 2
- ✓ Heat level classification (BAIXO/MEDIO/ALTO/CRITICO) with nightlife vs. daytime thresholds, configurable without redeploy — Phase 2
- ✓ Telemetry recording per-batch pipeline metrics (throughput, duration, recent-history view) — Phase 2
- ✓ Live dashboard (heat layer + severity markers + counts) polling a REST API every 10 seconds — Phase 3

### Active

- [ ] Open Exchange submission package (app + README) and Portuguese Developer Community article documenting AI tools/prompts and the PyProd approach

### Out of Scope

- Real live "how busy is this place" data source — no free, ToS-compliant option exists; popularity is a documented synthetic estimate, not a measurement (see `specs/popularity-model.spec`)
- RAG bonus track — PyProd is the natural fit for an ingestion pipeline; RAG has no natural fit for a heat map, and there's no time to pursue both
- Multi-city / multi-region support — single bounding box for v1; changing coverage is a config change, not a v1 feature (see `specs/venue-sourcing.spec` R3)
- Authentication / user accounts — dashboard is public, read-only; a contest demo doesn't need login
- Historical trend charts or long-run analytics — telemetry is intentionally scoped to the most recent 20 batches, not a full historical log (see `specs/telemetry.spec` R5)

## Context

- **Contest:** InterSystems Portugal 2026 Programming Contest, PyProd track ("create an interoperability project using PyProd"). Submission window 2026-08-24 to 2026-09-21 — the deadline is the day after this project's kickoff (2026-09-20).
- **Contest requirements:** backend built on InterSystems products; app built using an AI coding agent; paired submission of one Open Exchange app (English) + one Portuguese Developer Community article documenting AI tools, prompts, and methodology; tagged `#Concurso #ConcursoProgramacaoIA #AIProgramContest`. Solo entry (no team).
- **No IRIS environment exists yet.** Setting up IRIS (Community Edition, Docker) is in scope as project work, not assumed infrastructure.
- **Six specs already exist** in `specs/` — `ingestion-pipeline.spec`, `telemetry.spec`, `heat-classification.spec`, `popularity-model.spec`, `venue-sourcing.spec`, `dashboard-api.spec` — written before this session. They are detailed, unambiguous, and treated as the authoritative source of business rules for v1 scope; requirements definition should map to them directly rather than re-deriving from scratch.
- **Venue eligibility** is restricted to OpenStreetMap `amenity` tags: bar, pub, restaurant, cafe, fast_food, nightclub.

## Constraints

- **Timeline**: Working live demo required by 2026-09-21 — about one day from kickoff. Drives aggressive scope-cutting and vertical-slice execution over completeness.
- **Tech stack**: Backend must run on InterSystems IRIS. The ingestion pipeline should specifically be built as an IRIS Interoperability Production using embedded Python (PyProd) to qualify for the contest's PyProd track.
- **Compliance**: Popularity must never depend on a live scraped or ToS-violating "busy now" source — synthetic model only, per `specs/popularity-model.spec`.
- **Submission format**: The deliverable must package as an Open Exchange application (English-language) with an accompanying Portuguese-language article — this shapes README/documentation needs, not just code.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Target the PyProd bonus track, not RAG | The ingestion pipeline already maps naturally onto an interoperability production; RAG has no natural fit for a heat map | Shipped Phase 2 — IRIS Interoperability Production with embedded Python business hosts |
| Use `specs/*.spec` as the authoritative requirements source | Specs already exist, are detailed and unambiguous, and rewriting them would waste scarce time before the deadline | Shipped Phases 1-3 — all requirement IDs traced to spec files |
| Single city / single bounding box for v1 | The contest deadline leaves no time for multi-region catalog management | Shipped Phase 1 — Porto Ribeira/Sé/Baixa-Aliados historic center, config-only to change |
| Popularity is synthetic, not real telemetry | No free, ToS-compliant live "busy" API exists; documented as a modeled estimate | Shipped Phase 2 — category-specific daily curves, disclaimed in dashboard UI copy |
| Dashboard API is unauthenticated (AutheEnabled=64) | Public, read-only, no-PII contest demo; login-free public view is the explicit deliverable | Shipped Phase 3 — accepted risk AR-03-02, documented in 03-SECURITY.md |
| Dedup key is exact name + coordinates rounded to 5 decimals (round-half-up) | OSM has no canonical venue ID across duplicate node/way/relation entries; name+location is the only available signal | Shipped Phase 1 |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-09-21 after Phase 3*
