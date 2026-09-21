---
phase: "03"
slug: "dashboard-api"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-09-21"
---

# Phase 03 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Public internet -> PopHeat.API (%CSP.REST) | Untrusted client GET requests reach /csp/popheat/api/{venues,counts,telemetry,status}; unauthenticated by design (D-06) | Read-only JSON responses; no request body accepted |
| Public internet -> dashboard.html (static CSP page) | Untrusted clients load and execute the page's HTML/JS in their own browser | Static HTML/JS/CSS, no secrets embedded |
| PopHeat.API -> PopHeat.Reading / PopHeat.BatchTelemetry | Read-only embedded SQL queries against Phase 2's persisted data; the API never writes | Venue readings, heat levels, batch telemetry |
| dashboard.html -> CDN (unpkg.com) | The browser loads Leaflet/Leaflet.heat JS/CSS from a third-party CDN at runtime | Third-party script/style payloads |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-03-01 | Tampering | PopHeat.API GET routes | high | mitigate | All four routes accept zero user-supplied query/path parameters; every SQL statement is a fixed, parameterless embedded-SQL string — verified `grep -inE 'insert \|update \|delete '` against `iris/PopHeat/API.cls` returns zero matches | closed |
| T-03-02 | Information Disclosure | PopHeat.API Status() method | medium | mitigate | `Status()` (`iris/PopHeat/API.cls`) wraps `Ens.Director.IsProductionRunning` in Try/Catch, defaults `running=0` before the call and on any exception — never surfaces a raw IRIS error/stack trace | closed |
| T-03-03 | Denial of Service | PopHeat.API (all routes), unauthenticated + unrate-limited | low | accept | Single-container demo deployment for a judged contest window, not a multi-tenant production service; all queries hit indexed columns or a capped TOP-20 result set | closed (accepted) |
| T-03-04 | Elevation of Privilege | /csp/popheat/api and /csp/popheat (both AutheEnabled=64, unauthenticated) | low | accept | Deliberate per D-06/UI-SPEC: public, read-only dashboard, no PII, no write operations, no secrets | closed (accepted) |
| T-03-05 | Tampering | PopHeat.API SQL statements against PopHeat.Reading/BatchTelemetry | high | mitigate | Every REST classmethod issues SELECT-only SQL; no INSERT/UPDATE/DELETE keyword anywhere in `PopHeat.API.cls` (same evidence as T-03-01) | closed |
| T-03-06 | Tampering | dashboard.html's CDN-loaded Leaflet/Leaflet.heat script/link tags | medium | mitigate | Subresource Integrity (`integrity=` + `crossorigin="anonymous"`) pinned on all 3 CDN tags — verified at `iris/PopHeat/www/dashboard.html:33-34,387-391` | closed |
| T-03-07 | Tampering (Stored/Reflected XSS) | dashboard.html popup rendering of OSM-sourced venue fields | medium | mitigate | OSM-sourced venue name/category/heat-level/popularity/timestamp are HTML-escaped via `escapeHtml()` before being concatenated into popup markup — verified at `iris/PopHeat/www/dashboard.html:451,557-561`. Discovered and closed during 03-02 execution (03-02-SUMMARY.md deviation 4), not part of the original PLAN register — added here for completeness | closed |

*Status: open · closed · open — below {block_on} threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-03-01 | T-03-03 | Unauthenticated, unrate-limited API is acceptable for a single-container contest demo deployment; not a multi-tenant production service. Out of scope for the one-day timeline. | Jean Cruz | 2026-09-21 |
| AR-03-02 | T-03-04 | Public, read-only, no-PII dashboard is a deliberate product requirement (D-06) — a login-free public view is the explicit contest-demo deliverable. | Jean Cruz | 2026-09-21 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-09-21 | 7 | 7 | 0 | gsd-secure-phase (L1 grep-depth, register authored at plan time; T-03-07 added retroactively from 03-02-SUMMARY.md Threat Flags) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-09-21
