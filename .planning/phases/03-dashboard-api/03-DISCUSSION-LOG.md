# Phase 3: Dashboard & API - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-20
**Phase:** 3-Dashboard & API
**Areas discussed:** Map/tile provider, REST API implementation layer, Frontend delivery mechanism, Heat-level color scheme, Production-status & fetch-error UX

**Mode:** `--auto` — fully autonomous, no user prompts. Every option below was auto-selected as the recommended default and logged for audit; no AskUserQuestion calls were made.

---

## Map/tile provider

| Option | Description | Selected |
|--------|-------------|----------|
| Leaflet.js + OpenStreetMap tiles | No API key, free, well-documented | ✓ |
| Mapbox GL JS | More polished styling, but requires an API key/account signup | |

**User's choice (auto-selected):** Leaflet.js + OpenStreetMap tiles
**Notes:** Zero setup risk for a one-day build; matches the OSM provenance of the venue catalog itself.

---

## REST API implementation layer

| Option | Description | Selected |
|--------|-------------|----------|
| Native IRIS `%CSP.REST` class in the existing container | No new service; queries IRIS SQL directly | ✓ |
| Separate Python (Flask/FastAPI) service + IRIS DB driver | More familiar tooling, but adds a second container/service to the compose stack | |

**User's choice (auto-selected):** Native IRIS `%CSP.REST` class
**Notes:** Keeps the stack to one docker-compose service, consistent with Phase 2's single-namespace/single-service decisions (D-03/D-04).

---

## Frontend delivery mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Single static HTML page (vanilla JS + Leaflet CDN) served via IRIS CSP | Zero build toolchain, zero new dependencies | ✓ |
| Node/npm-based frontend (React/Vite etc.) | More scalable for a larger app, but adds build tooling and a separate dev/deploy story not needed here | |

**User's choice (auto-selected):** Single static HTML page via IRIS CSP
**Notes:** Fits the one-day timeline; no bundler or npm install step required on demo day.

---

## Heat-level color scheme

| Option | Description | Selected |
|--------|-------------|----------|
| Green → yellow → orange → red gradient | Standard, intuitive heat-map semantics | ✓ |
| Custom brand palette | More distinctive, but adds design time with no functional benefit | |

**User's choice (auto-selected):** Green → yellow → orange → red gradient
**Notes:** Matches the "heat" framing of the product name itself; intuitive at a glance for contest judges.

---

## Production-status & fetch-error UX

| Option | Description | Selected |
|--------|-------------|----------|
| Small non-blocking status badge + dismissible stale-data banner on fetch failure | Matches R6 (informational only, never gates data) and R7 (visible error state) literally | ✓ |
| Full-page error/loading states that block the map | Simpler to implement but explicitly contradicts R6's "keep serving last-known data" requirement | |

**User's choice (auto-selected):** Small badge + dismissible banner
**Notes:** R6 and R7 both explicitly require the dashboard to keep showing data through failures — a blocking error state would violate this.

---

## Claude's Discretion

- Exact REST endpoint paths/shapes.
- Exact minimum visible weight for low-popularity venues on the heat layer.
- Exact marker pixel sizes for CRITICO vs. ALTO (any CRITICO > ALTO relationship satisfies the requirement).
- Detailed visual layout beyond the map — deferred to a dedicated `/gsd-ui-phase` pass (ROADMAP.md marks this phase "UI hint: yes").

## Deferred Ideas

None — discussion stayed within phase scope.
