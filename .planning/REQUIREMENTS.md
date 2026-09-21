# Requirements: PopHeat

**Defined:** 2026-09-20
**Core Value:** A working, submittable IRIS PyProd application, live and functioning end-to-end (ingest → score → classify → persist → dashboard), by the contest deadline

## v1 Requirements

Derived directly from `specs/*.spec` (already-decided business rules) plus the InterSystems Portugal 2026 Programming Contest submission requirements. No domain research was run — the specs are the authoritative source given the one-day timeline.

### Venue Sourcing

- [x] **VENU-01**: Venue catalog includes only OSM places tagged `amenity` = bar, pub, restaurant, cafe, fast_food, or nightclub
- [x] **VENU-02**: Places missing name, latitude, longitude, or amenity tag are discarded from the catalog
- [x] **VENU-03**: Venue catalog is scoped to one configured bounding box (one city area); changing coverage only requires changing that config, no code change
- [x] **VENU-04**: A venue is dropped as a duplicate if another entry shares the same name and coordinates rounded to 5 decimal places
- [x] **VENU-05**: Each venue keeps a stable identifier derived from its OSM source record
- [x] **VENU-06**: The venue catalog is a static snapshot regenerated on demand, not recomputed on every ingestion cycle

### Ingestion Pipeline

- [x] **INGE-01**: Ingestion is implemented as an IRIS Interoperability Production using embedded Python (PyProd)
- [x] **INGE-02**: Venues are processed in batches of 150, with 3 seconds between the start of one batch and the next
- [x] **INGE-03**: Ingestion cycles through the full venue catalog continuously, wrapping to the start after reaching the end
- [x] **INGE-04**: A batch of venues is scored, classified, and persisted as one atomic unit; venues are never split across pipeline stages mid-batch
- [x] **INGE-05**: A failure while processing one batch is recorded as an error for that batch without stopping the next scheduled batch
- [x] **INGE-06**: Every persisted reading carries venue identity, name, category, coordinates, popularity, heat level, and observation timestamp
- [x] **INGE-07**: Persisting a reading always inserts a new row; historical readings are retained, never overwritten

### Popularity Model

- [x] **POPU-01**: Popularity score is always between 0.02 and 0.98, rounded to 3 decimal places
- [x] **POPU-02**: Each venue category follows its own peak-hour curve (cafe, restaurant, fast_food, bar, pub, nightclub, and a generic fallback for any other category)
- [x] **POPU-03**: Time distance to a peak hour wraps at midnight (the day is circular)
- [x] **POPU-04**: Score is boosted 20% from Friday through Sunday, before clamping to the valid range
- [x] **POPU-05**: A small random adjustment (-0.06 to +0.06) is applied to every reading
- [x] **POPU-06**: Popularity is recalculated fresh on every ingestion cycle, never stored or reused between cycles

### Heat Classification

- [x] **HEAT-01**: Every reading is classified into exactly one of BAIXO, MEDIO, ALTO, CRITICO
- [x] **HEAT-02**: Nightlife categories (bar, pub, nightclub) use a lower popularity threshold scale than daytime categories
- [x] **HEAT-03**: Thresholds are stored as configuration, adjustable without a code change or redeploy
- [x] **HEAT-04**: A reading that can't be classified defaults to BAIXO rather than being left unlabeled or rejected

### Telemetry

- [x] **TELE-01**: Exactly one telemetry record is written per persisted batch
- [x] **TELE-02**: Each telemetry record captures reading count, elapsed persist time, throughput, and timestamp
- [x] **TELE-03**: Throughput is computed as batch size divided by elapsed time, reporting zero (not divide-by-zero or omitted) when elapsed time is zero or unavailable
- [x] **TELE-04**: A telemetry-recording failure never blocks persistence of the venue readings themselves
- [x] **TELE-05**: Operational views show only the most recent 20 batches, not the full historical telemetry log

### Dashboard & API

- [x] **DASH-01**: Venue-facing views always show each venue's latest reading only; older readings are never shown as current state
- [ ] **DASH-02**: The heat map includes every venue with at least one reading, weighted by popularity, with a minimum visible weight for low-popularity venues
- [ ] **DASH-03**: Only ALTO/CRITICO venues get individual clickable markers; BAIXO/MEDIO venues appear on the heat layer only
- [ ] **DASH-04**: A CRITICO marker renders larger than an ALTO marker
- [x] **DASH-05**: Displayed heat-level counts are computed from the same "latest reading per venue" rule as DASH-01, never inflated by historical readings
- [ ] **DASH-06**: The dashboard shows whether the ingestion pipeline is currently running, but keeps serving last-known data regardless of that status
- [x] **DASH-07**: The dashboard re-fetches venues, counts, and telemetry every 10 seconds; a fetch failure shows a visible error state rather than silently keeping stale data displayed as current

### Contest Submission

- [ ] **SUBM-01**: Application is published to the InterSystems Open Exchange with an English-language listing
- [ ] **SUBM-02**: An accompanying article is published on the Portuguese Developer Community, tagged `#Concurso #ConcursoProgramacaoIA #AIProgramContest`
- [ ] **SUBM-03**: The article documents the AI tools, prompts, and methodology used to build the project
- [ ] **SUBM-04**: The Open Exchange application and the article link to each other, per the contest's paired-submission rule

## v2 Requirements

None. Given the one-day timeline, everything not needed for a working, submittable v1 is Out of Scope rather than deferred — there is no v2 cycle planned for this milestone.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real live "how busy" data source | No free, ToS-compliant option exists; popularity is a documented synthetic estimate, not a measurement |
| RAG bonus track | PyProd is the natural fit for an ingestion pipeline; no time to pursue both bonus tracks |
| Multi-city / multi-region support | Single bounding box for v1; changing coverage is a future config change, not a v1 feature |
| Authentication / user accounts | Dashboard is public and read-only; a contest demo doesn't need login |
| Historical trend charts / long-run analytics | Telemetry is intentionally scoped to the most recent 20 batches, not a full historical log |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| VENU-01 | Phase 1 | Complete |
| VENU-02 | Phase 1 | Complete |
| VENU-03 | Phase 1 | Complete |
| VENU-04 | Phase 1 | Complete |
| VENU-05 | Phase 1 | Complete |
| VENU-06 | Phase 1 | Complete |
| INGE-01 | Phase 2 | Complete |
| INGE-02 | Phase 2 | Complete |
| INGE-03 | Phase 2 | Complete |
| INGE-04 | Phase 2 | Complete |
| INGE-05 | Phase 2 | Complete |
| INGE-06 | Phase 2 | Complete |
| INGE-07 | Phase 2 | Complete |
| POPU-01 | Phase 2 | Complete |
| POPU-02 | Phase 2 | Complete |
| POPU-03 | Phase 2 | Complete |
| POPU-04 | Phase 2 | Complete |
| POPU-05 | Phase 2 | Complete |
| POPU-06 | Phase 2 | Complete |
| HEAT-01 | Phase 2 | Complete |
| HEAT-02 | Phase 2 | Complete |
| HEAT-03 | Phase 2 | Complete |
| HEAT-04 | Phase 2 | Complete |
| TELE-01 | Phase 2 | Complete |
| TELE-02 | Phase 2 | Complete |
| TELE-03 | Phase 2 | Complete |
| TELE-04 | Phase 2 | Complete |
| TELE-05 | Phase 2 | Complete |
| DASH-01 | Phase 3 | Complete |
| DASH-02 | Phase 3 | Pending |
| DASH-03 | Phase 3 | Pending |
| DASH-04 | Phase 3 | Pending |
| DASH-05 | Phase 3 | Complete |
| DASH-06 | Phase 3 | Pending |
| DASH-07 | Phase 3 | Complete |
| SUBM-01 | Phase 4 | Pending |
| SUBM-02 | Phase 4 | Pending |
| SUBM-03 | Phase 4 | Pending |
| SUBM-04 | Phase 4 | Pending |

**Coverage:**

- v1 requirements: 39 total (corrected during roadmap creation — the original count of 34 in this section undercounted the requirement checklist above; 39 is the actual count of listed REQ-IDs)
- Mapped to phases: 39
- Unmapped: 0 ✓

---
*Requirements defined: 2026-09-20*
*Last updated: 2026-09-20 after roadmap creation (4 phases, 100% coverage)*
