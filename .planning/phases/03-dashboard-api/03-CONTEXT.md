# Phase 3: Dashboard & API - Context

**Gathered:** 2026-09-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Serve a live, auto-refreshing public dashboard showing current venue crowdedness on a map, backed by a REST API that reads Phase 2's persisted `PopHeat.Reading` and `PopHeat.BatchTelemetry` data. This phase adds no new data — it is a read-only presentation layer over what Phase 2 already produces every 3 seconds.

</domain>

<decisions>
## Implementation Decisions

### Map & Visuals
- **D-01:** Map is built with Leaflet.js using the OpenStreetMap tile layer — no API key, no paid tile provider, no signup step, matching the OSM provenance of the venue data itself.
- **D-02:** Heat levels use a green (BAIXO) → yellow (MEDIO) → orange (ALTO) → red (CRITICO) color gradient — standard, intuitive "heat" semantics that match the product's own name and framing.

### REST API & Backend
- **D-03:** The REST API is implemented as a native IRIS `%CSP.REST` class inside the existing `POPHEAT` namespace/container — no new service, no new container, no second language runtime. It queries `PopHeat.Reading`/`PopHeat.BatchTelemetry` directly via embedded SQL. — **Reversibility:** costly — switching to a separate API service later means re-authoring all routes and redeploying a second container.
- **D-04:** "Latest reading per venue" (R1/DASH-01) and the matching heat-level counts (R5/DASH-05) are both computed via the same underlying grouped-by-venue query (e.g. `MAX(ObservedAt)` per `VenueId`, following Phase 2's D-07 decision that there is no separate "latest" table) — a single source of truth for both the map and the counts, so they can never drift apart.

### Frontend Delivery
- **D-05:** The dashboard is a single static HTML page (vanilla JS + Leaflet loaded from CDN) served as a static IRIS CSP page from the same container — no Node/npm build toolchain, no bundler, no separate static file server.

### Status & Error Handling
- **D-06:** Pipeline running-status (DASH-06/R6) is surfaced via a small, non-blocking status badge that queries `Ens.Director.IsProductionRunning("PopHeat.Production")` through the same REST API; it is purely informational and never gates or blanks the displayed venue/heat data.
- **D-07:** A fetch failure (DASH-07/R7) shows a dismissible banner reading "Unable to refresh — showing last known data as of {last successful fetch time}" — the last successfully fetched data stays visible and clearly marked as stale, never silently replaced or blanked.
- **D-08:** Client refresh cadence is exactly 10 seconds (R7), matching the spec literally — not tied to or derived from Phase 2's 3-second ingestion cadence.

### Claude's Discretion
- Exact REST endpoint paths/shapes (e.g. `/api/venues`, `/api/counts`, `/api/telemetry`) — pin during planning.
- Exact minimum visible weight value for low-popularity venues on the heat layer (R2/DASH-02) — pin a reasonable default during planning/research.
- Exact marker size values for CRITICO vs. ALTO (R4/DASH-04) — any CRITICO-larger-than-ALTO relationship satisfies the requirement; exact pixel values are an implementation detail.
- Visual layout beyond the map itself (header, counts display, telemetry view) — this phase has "UI hint: yes" in ROADMAP.md, so a dedicated `/gsd-ui-phase` design contract pass is expected before/alongside detailed planning.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Dashboard & API Rules
- `specs/dashboard-api.spec` — Authoritative rules for this phase: latest-reading-only views (R1), heat map weighting (R2), marker visibility/prominence rules (R3/R4), count consistency (R5), non-gating production status (R6), 10-second refresh cadence with visible error state (R7).

### Upstream Data Contract (Phase 2)
- `.planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/02-CONTEXT.md` — D-06 (persistence schema: `PopHeat.Reading`/`PopHeat.BatchTelemetry` as separate SQL-projected classes), D-07 (insert-only, no separate "latest" table — this phase MUST compute "latest" itself via a grouped query, not assume one exists).
- `popheat_pipeline/components.py`, `iris/PopHeat/Reading.cls`, `iris/PopHeat/BatchTelemetry.cls` — the exact schema/field names this phase's API queries against.

### Project-Level
- `.planning/PROJECT.md` — Core value, IRIS/PyProd constraint (note: this phase's REST layer is native IRIS, not PyProd — PyProd requirement is already satisfied by Phase 2).
- `.planning/REQUIREMENTS.md` — DASH-01 through DASH-07, the requirements this phase covers.

</canonical_refs>

<code_context>
## Existing Code Insights

Phase 2 delivered the full backend: a single IRIS container (`docker-compose.yml`) with `PopHeat.Reading` and `PopHeat.BatchTelemetry` as SQL-queryable Persistent classes, both accumulating rows continuously. No frontend, no REST layer, no `%CSP.REST` classes exist yet — this phase is greenfield for presentation.

### Reusable Assets
- `PopHeat.Reading` / `PopHeat.BatchTelemetry` — the exact tables this phase's API reads from; field names already fixed by Phase 2 (`VenueId`, `VenueName`, `Category`, `Latitude`, `Longitude`, `Popularity`, `HeatLevel`, `ObservedAt` / `ReadingCount`, `ElapsedSeconds`, `Throughput`, `RecordedAt`).
- `PopHeat.BatchTelemetry.RecentBatches()` — an existing `%SQLQuery` capped at 20 rows (Phase 2, TELE-05) — this phase's telemetry endpoint can query or wrap this directly rather than re-deriving the "recent 20" logic.

### Established Patterns
- Single-container, single-namespace discipline (Phase 2 D-03/D-04) carries forward — no new services added in this phase either.

### Integration Points
- This phase reads Phase 2's `PopHeat.Reading`/`PopHeat.BatchTelemetry` tables; it writes nothing back to them.

</code_context>

<specifics>
## Specific Ideas

- Zero-API-key, zero-new-dependency bias throughout (Leaflet+OSM, native IRIS REST, static HTML) is deliberate given the one-day contest timeline — every choice here trades "more polished/scalable" for "guaranteed to work on demo day with no external signup or paid service."

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 3-Dashboard & API*
*Context gathered: 2026-09-20*
