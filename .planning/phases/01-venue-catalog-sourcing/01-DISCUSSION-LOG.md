# Phase 1: Venue Catalog Sourcing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-20
**Phase:** 1-Venue Catalog Sourcing
**Areas discussed:** City & bounding box, Data source strategy, Catalog output format, Regeneration trigger

---

## City & Bounding Box

| Option | Description | Selected |
|--------|-------------|----------|
| Lisbon (city center) | Capital, dense bar/restaurant/nightlife scene | |
| Porto (city center) | Second city, also dense nightlife/food scene | ✓ |
| Other city | User-specified | |

**User's choice:** Porto (city center)

| Option | Description | Selected |
|--------|-------------|----------|
| Tight historic center (~50-150 venues) | Just Ribeira/Baixa/Aliados — small, fast to fetch | ✓ |
| Historic center + Vila Nova de Gaia riverside (~150-400 venues) | Adds Gaia riverfront | |
| You decide | Claude sizes to clear ~150 venues | |

**User's choice:** Tight historic center (~50-150 venues)

| Option | Description | Selected |
|--------|-------------|----------|
| Ribeira + Sé + Baixa/Aliados | Classic tourist/nightlife core along the riverfront up to Aliados | ✓ |
| Above + Cedofécita/Galeria de Paris | Extends north to bar-heavy nightlife strip | |
| You decide | Claude picks coords in the ~50-150 venue range | |

**User's choice:** Ribeira + Sé + Baixa/Aliados

| Option | Description | Selected |
|--------|-------------|----------|
| Leave to research/planning | Precise lat/lon bounds looked up during research | ✓ |
| I'll give exact coordinates now | User provides bounds directly | |

**User's choice:** Leave to research/planning

**Notes:** User is aiming for a demo that "looks full" — venue density in a tight, recognizable box mattered more than geographic breadth.

---

## Data Source Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Overpass API, live query | Query public Overpass API at build time | ✓ |
| Overpass API, fetch once + cache to committed snapshot | Cache reduces demo-day dependency risk | |
| You decide | Claude balances simplicity vs. reliability | |

**User's choice:** Overpass API, live query

| Option | Description | Selected |
|--------|-------------|----------|
| Fail loudly, keep last good catalog | Error out, leave previous catalog file untouched | ✓ |
| Fail loudly, no fallback needed | Error out, no special handling | |
| You decide | Claude picks reasonable failure handling | |

**User's choice:** Fail loudly, keep last good catalog

| Option | Description | Selected |
|--------|-------------|----------|
| Public overpass-api.de only | Standard public instance, no failover | ✓ |
| Try overpass-api.de, fall back to a mirror | Adds resilience, more complexity | |
| You decide | Claude picks simplest reliable option | |

**User's choice:** Public overpass-api.de only

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, save raw response alongside the catalog | Keeps raw Overpass JSON for debugging | ✓ |
| No, catalog output only | Only final processed catalog written | |

**User's choice:** Yes, save raw response alongside the catalog

**Notes:** User accepted the demo-day risk of a live external dependency in exchange for simplicity, but paired it with a "keep last good catalog on failure" safety net.

---

## Catalog Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON file | One JSON array of venue objects, easy for Python to read | ✓ |
| CSV file | Flat tabular, awkward for nested OSM tags | |
| You decide | Claude picks simplest format for both consumers | |

**User's choice:** JSON file

| Option | Description | Selected |
|--------|-------------|----------|
| data/venues.json | Top-level data/ directory, stable path | ✓ |
| You decide | Claude picks a path fitting the eventual repo structure | |

**User's choice:** data/venues.json

| Option | Description | Selected |
|--------|-------------|----------|
| Lock it now: id, name, category, lat, lon | Minimal fields per spec R2/R5 | |
| Leave to research/planning | Finalize field names/types once Phase 2 consumption is researched | ✓ |

**User's choice:** Leave to research/planning

| Option | Description | Selected |
|--------|-------------|----------|
| Commit it to git | Demo doesn't depend on re-running the build step | |
| Gitignore it (build artifact) | Treated purely as generated output | ✓ |
| You decide | Claude picks based on demo-day reliability | |

**User's choice:** Gitignore it (build artifact)

---

## Regeneration Trigger

| Option | Description | Selected |
|--------|-------------|----------|
| Standalone Python CLI script | Runs outside IRIS, no Phase 2 dependency | (implied by "You decide") |
| You decide | Claude picks simplest invocation mechanism | ✓ |

**User's choice:** You decide → Claude selected standalone Python CLI script (e.g. `python scripts/build_catalog.py`), since no IRIS environment exists yet and Phase 1 has no dependency on Phase 2's IRIS setup.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, print a summary | Venue counts, drops, duplicates on completion | ✓ |
| No, silent unless it fails | Only output on error | |

**User's choice:** Yes, print a summary

| Option | Description | Selected |
|--------|-------------|----------|
| Just overwrite, no confirmation | Simplest, no interactive prompt | ✓ |
| Back up the previous file before overwriting | Cheap rollback safety net | |

**User's choice:** Just overwrite, no confirmation

| Option | Description | Selected |
|--------|-------------|----------|
| Separate config file | Matches spec R3's config-only-change requirement | ✓ |
| Constants at the top of the script | Simpler but is a code change | |
| You decide | Claude picks least complex option satisfying R3 | |

**User's choice:** Separate config file

---

## Claude's Discretion

- Exact bounding-box lat/lon coordinates for Ribeira + Sé + Baixa/Aliados.
- Exact per-venue JSON field names/types beyond the minimum required set (id, name, category, lat, lon).
- Invocation mechanism for the build step — resolved to a standalone Python CLI script.

## Deferred Ideas

None — discussion stayed within phase scope.
