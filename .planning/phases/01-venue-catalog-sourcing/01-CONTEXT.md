# Phase 1: Venue Catalog Sourcing - Context

**Gathered:** 2026-09-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a deduplicated venue catalog for one Porto city-center bounding box, sourced from OpenStreetMap. The catalog is a static snapshot (venue identity, name, category, coordinates) produced by an on-demand build step — not recomputed on every ingestion cycle. It is the sole input Phase 2's IRIS PyProd pipeline will read from; no popularity/heat computation happens in this phase.

</domain>

<decisions>
## Implementation Decisions

### City & Bounding Box
- **D-01:** Bounding box covers Porto's historic center — Ribeira + Sé + Baixa/Aliados — targeting roughly 50-150 venues.
- **D-02:** Exact lat/lon bounds are not pinned here — research/planning will look up precise coordinates for these districts sized to the venue-count target, and record the exact numbers in the plan.

### Data Source Strategy
- **D-03:** Fetch venue data via a live Overpass API query at build time (not a pre-fetched/cached snapshot as the default path).
- **D-04:** Query only the public `overpass-api.de` endpoint — no mirror/fallback endpoint.
- **D-05:** If the Overpass query fails or times out, the build step fails loudly (non-zero exit, clear error) and leaves the previously-generated `data/venues.json` untouched, so the pipeline keeps running on the last known-good catalog rather than being left with nothing.
- **D-06:** The build step also saves the raw Overpass JSON response alongside the generated catalog, for debugging/reproducibility.

### Catalog Output Format
- **D-07:** Catalog is written as a JSON file at `data/venues.json`.
- **D-08:** Exact per-venue field names/types are not locked here — left to research/planning, informed by how Phase 2's PyProd production will consume the file. Minimum content per `specs/venue-sourcing.spec` R2/R5: stable id, name, category (amenity tag), latitude, longitude.
- **D-09:** `data/venues.json` (and the raw Overpass snapshot from D-06) are gitignored — treated as generated build artifacts, not committed to source control. — **Reversibility:** reversible — easy to un-gitignore later if needed.

### Regeneration Trigger
- **D-10:** Regeneration is invoked as a standalone Python CLI script (e.g. `python scripts/build_catalog.py`), run outside IRIS — Claude's discretion, since no IRIS environment exists yet and Phase 1 has no dependency on Phase 2's IRIS setup.
- **D-11:** The script prints a run summary on completion (venues fetched, dropped for missing fields, dropped as duplicates, final catalog count) — useful for demo-day sanity checks.
- **D-12:** The script overwrites `data/venues.json` on every run with no confirmation prompt and no backup of the previous file.
- **D-13:** Bounding box and other build parameters (city area, amenity tag allowlist) live in a separate config file, not hardcoded constants — this is what makes changing coverage a config-only change per `specs/venue-sourcing.spec` R3.

### Claude's Discretion
- Exact bounding-box lat/lon coordinates for Ribeira + Sé + Baixa/Aliados (D-02).
- Exact per-venue JSON field names/types beyond the minimum required set (D-08).
- Invocation mechanism for the build step, confirmed as a standalone Python CLI script (D-10).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Venue Sourcing Rules
- `specs/venue-sourcing.spec` — Authoritative business rules for this phase: eligibility tags (R1), required fields (R2), bounding-box scope (R3), 5-decimal dedup (R4), stable identity (R5), manual/on-demand regeneration (R6).

### Downstream Consumer (context only — not implemented in this phase)
- `specs/ingestion-pipeline.spec` — Defines how Phase 2 will read/walk the catalog (batches of 150, full-catalog cycling). Referenced here because it shapes the D-08 field-naming decision (deferred to research) and confirms this phase has no IRIS dependency.

### Project-Level
- `.planning/PROJECT.md` — Core value, constraints, venue eligibility tags.
- `.planning/REQUIREMENTS.md` — VENU-01 through VENU-06, the requirements this phase covers.

</canonical_refs>

<code_context>
## Existing Code Insights

Repository is greenfield for this phase — only `specs/*.spec` and `.planning/` exist. No code, no established patterns, no reusable assets yet.

### Integration Points
- Output (`data/venues.json`) is the sole handoff point to Phase 2's IRIS PyProd production, which does not yet exist.

</code_context>

<specifics>
## Specific Ideas

- City choice: Porto, not Lisbon — the user's preference for this demo.
- District scope: Ribeira + Sé + Baixa/Aliados specifically (the classic riverside/downtown tourist-and-nightlife core), not extended north into Cedofécita/Galeria de Paris and not extended across the river into Vila Nova de Gaia.
- Reliability posture: the user explicitly chose live Overpass querying over a cached snapshot, accepting the demo-day risk in exchange for simplicity — but paired it with "keep last good catalog on failure" so a bad run doesn't wipe out a working demo.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Venue Catalog Sourcing*
*Context gathered: 2026-09-20*
