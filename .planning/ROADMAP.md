# Roadmap: PopHeat

## Overview

PopHeat ships as four horizontal technical layers, built and integrated in sequence under an
extreme one-day timeline: first the static venue catalog sourced from OpenStreetMap, then the
IRIS Interoperability Production (PyProd) that continuously ingests that catalog in batches,
computes synthetic popularity, classifies heat levels, persists readings, and records telemetry,
then the REST API and live dashboard that surface that data, and finally the contest submission
packaging. Each layer is a complete technical slice — nothing user-visible exists until Phase 3,
but each layer is independently buildable and verifiable before the next one depends on it.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Venue Catalog Sourcing** - Build a deduplicated OSM venue catalog for one city bounding box (completed 2026-09-20)
- [x] **Phase 2: IRIS Ingestion Pipeline — Scoring, Classification & Telemetry** - Stand up IRIS + a PyProd production that continuously ingests, scores, classifies, persists, and records telemetry for the venue catalog (completed 2026-09-20)
- [ ] **Phase 3: Dashboard & API** - Serve a live, auto-refreshing heat map and REST API over persisted readings
- [ ] **Phase 4: Contest Submission Packaging** - Publish the paired Open Exchange app + Portuguese Developer Community article

## Phase Details

### Phase 1: Venue Catalog Sourcing

**Goal**: A real, deduplicated venue catalog for one city bounding box exists for the pipeline to ingest
**Depends on**: Nothing (first phase)
**Requirements**: VENU-01, VENU-02, VENU-03, VENU-04, VENU-05, VENU-06
**Success Criteria** (what must be TRUE):

  1. Building the catalog against OpenStreetMap for the configured bounding box yields only venues tagged bar, pub, restaurant, cafe, fast_food, or nightclub, and changing the bounding box is a config-only change
  2. Places missing a name, latitude, longitude, or amenity tag are excluded from the generated catalog
  3. No two catalog entries share the same name and coordinates rounded to 5 decimal places
  4. Every catalog venue carries a stable identifier derived from its OSM source record
  5. The catalog is produced by an on-demand build step, not recomputed automatically on every ingestion cycle

**Plans**: 2/2 plans executed

Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Config-driven Overpass fetch -> filtered catalog write, end-to-end (tracer)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Deduplication + run() overwrite/empty-result semantics

### Phase 2: IRIS Ingestion Pipeline — Scoring, Classification & Telemetry

**Goal**: A running IRIS Interoperability Production continuously ingests the venue catalog in batches, computes popularity, classifies heat level, persists readings, and records operational telemetry — resiliently and without manual intervention
**Depends on**: Phase 1
**Requirements**: INGE-01, INGE-02, INGE-03, INGE-04, INGE-05, INGE-06, INGE-07, POPU-01, POPU-02, POPU-03, POPU-04, POPU-05, POPU-06, HEAT-01, HEAT-02, HEAT-03, HEAT-04, TELE-01, TELE-02, TELE-03, TELE-04, TELE-05
**Success Criteria** (what must be TRUE):

  1. IRIS Community Edition runs in Docker with a deployed Interoperability Production built in embedded Python (PyProd) that processes the venue catalog in batches of 150, 3 seconds apart, wrapping continuously back to the start of the catalog once it reaches the end
  2. Each batch is scored, classified, and persisted as one atomic unit, and a failure while processing one batch is recorded as an error for that batch without stopping the next scheduled batch
  3. Every persisted reading carries venue identity, name, category, coordinates, popularity score, heat level, and observation timestamp, and is always inserted as a new row — prior readings for a venue are never overwritten
  4. Popularity scores are always between 0.02 and 0.98 rounded to 3 decimals, follow each category's own peak-hour curve with midnight-wrapping time distance, receive a Friday-through-Sunday 20% boost before clamping, carry a small random adjustment on every reading, and are never cached or reused between cycles
  5. Every reading is classified into exactly one of BAIXO/MEDIO/ALTO/CRITICO using nightlife vs. daytime threshold sets that are stored as adjustable configuration (no redeploy needed) and default to BAIXO when a reading can't otherwise be classified
  6. Every persisted batch writes exactly one telemetry record (reading count, elapsed persist time, throughput, timestamp) that never blocks reading persistence if telemetry recording fails, and operational views expose only the most recent 20 batches

**Plans**: 2/2 plans executed

Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Docker + IRIS + POPHEAT namespace + PopHeat.Production, one venue end-to-end (tracer)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Real 150/3s batching, wrap-around cycling, config-driven thresholds, failure isolation, and hardened telemetry

### Phase 3: Dashboard & API

**Goal**: A live, publicly viewable dashboard shows current venue crowdedness on a map, refreshed automatically, backed by a REST API over the persisted readings and telemetry
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06, DASH-07
**Success Criteria** (what must be TRUE):

  1. Venue-facing views (map, list, counts) always reflect only each venue's latest reading, and displayed heat-level counts are computed from that same latest-reading rule — older readings never appear as current state or inflate counts
  2. The heat map layer includes every venue with at least one reading, weighted by popularity, with a minimum visible weight applied so low-popularity venues stay visible
  3. Only venues currently classified ALTO or CRITICO get individual clickable markers, with a CRITICO marker rendering larger than an ALTO marker; BAIXO/MEDIO venues appear only on the heat layer
  4. The dashboard displays whether the ingestion pipeline is currently running, but keeps serving last-known data regardless of that status
  5. The dashboard auto-refreshes venues, counts, and telemetry every 10 seconds, and a fetch failure surfaces a visible error state rather than silently leaving stale data displayed as current

**Plans**: 2/3 plans executed

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — REST API (venues/counts/telemetry/status) + minimal end-to-end map (tracer)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Heat layer, ALTO/CRITICO markers, counts/telemetry panels, status badge, full UI-SPEC styling

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 03-03-PLAN.md — 10s auto-refresh loop, in-flight guard, stale-data error banner, empty state

**UI hint**: yes

### Phase 4: Contest Submission Packaging

**Goal**: The finished application and its supporting documentation are published per the contest's paired-submission rule
**Depends on**: Phase 3
**Requirements**: SUBM-01, SUBM-02, SUBM-03, SUBM-04
**Success Criteria** (what must be TRUE):

  1. The application is published on the InterSystems Open Exchange with an English-language listing
  2. A companion article is published on the Portuguese Developer Community, tagged #Concurso #ConcursoProgramacaoIA #AIProgramContest
  3. The article documents which AI tools, prompts, and methodology were used to build the project
  4. The Open Exchange listing and the article link to each other, per the contest's paired-submission rule

**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Venue Catalog Sourcing | 2/2 | Complete    | 2026-09-20 |
| 2. IRIS Ingestion Pipeline — Scoring, Classification & Telemetry | 2/2 | Complete    | 2026-09-20 |
| 3. Dashboard & API | 2/3 | In Progress|  |
| 4. Contest Submission Packaging | 0/TBD | Not started | - |
