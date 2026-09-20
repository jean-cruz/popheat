# API Coverage: Overpass API (Venue Catalog Sourcing)

**Detected:** `api-coverage.cjs` fired on CONTEXT.md D-03 ("Fetch venue data via a live Overpass API
query at build time"). Confirmed manually: this phase makes a real outbound integration against the
public Overpass API (`overpass-api.de`) — this IS an external API integration in scope for this phase.

**Default policy:** every capability starts as `INTEGRATE`; this table is the subtraction record.

| capability | decision | reason |
|---|---|---|
| query-by-bbox | INTEGRATE | Core mechanism for R3/VENU-03 geographic scope — bounding box supplied via Overpass QL `(south,west,north,east)` filter, sourced from `config/catalog_build.json` (D-01/D-02). |
| query-by-tag (amenity allowlist) | INTEGRATE | Core mechanism for R1/VENU-01 eligibility filtering — exact-match regex against the 6-value amenity allowlist. |
| node/way/relation element selection (`nwr` + `out center`) | INTEGRATE | Real-world OSM venues are tagged on nodes AND building ways; `out center` supplies `center.lat`/`center.lon` for ways/relations so they are not silently excluded. |
| output-format selection (`[out:json]`) | INTEGRATE | Explicit JSON output requested so the client parses structured data, not XML/CSV. |
| raw-response-capture | INTEGRATE | D-06 — the raw Overpass JSON response is saved verbatim to `data/venues.raw.json` alongside the generated catalog, for debugging/reproducibility. |
| timeout-handling (`[timeout:N]` + HTTP client timeout) | INTEGRATE | D-05 — a slow/unresponsive server must fail loudly (non-zero exit) rather than hang; both the Overpass server-side hint and the HTTP client timeout are set. |
| response-size bounding | INTEGRATE | Threat mitigation (see `<threat_model>` T-01-02) — an explicit byte-size ceiling is enforced on the read before `json.loads`, so an oversized/runaway response cannot exhaust memory or hang the build. |
| mirror/fallback endpoint | OPT-OUT | D-04 — explicit user decision: query only the public `overpass-api.de` endpoint, no mirror/fallback for v1. |
| authentication / API key | OPT-OUT | Overpass's public API is unauthenticated; no credential surface exists to integrate. |
| rate-limit/backoff/retry | OPT-OUT | Not needed yet — a single on-demand manual run (D-10/R6), not a sustained polling client; D-05's fail-loud-on-any-error already covers a 429 the same as any other failure, so no retry/backoff logic is built for v1. |
| historical/point-in-time query (date filter) | OPT-OUT | Not needed — the catalog always reflects the current OSM state; no historical/versioned query is required by any requirement. |
| incremental / augmented-diff sync | OPT-OUT | Not needed — R6/VENU-06 defines the catalog as a full on-demand snapshot rebuild, not an incremental sync. |
| multi-area / complex polygon geometry filter | OPT-OUT | Not needed — single bounding box only (D-01); multi-city/complex-region support is explicitly out of scope for v1 per REQUIREMENTS.md. |
| server status / quota endpoint (`/api/status`) | OPT-OUT | Not needed — a single ad-hoc script invocation, not a sustained service that needs to monitor its own quota usage. |

**No package installs.** The Overpass client is implemented with Python stdlib only (`urllib.request`,
`json`) — no `pip install` is introduced by this phase, so the package-legitimacy gate does not apply.
