---
phase: 03-dashboard-api
plan: 01
subsystem: api
tags: [csp-rest, objectscript, iris, leaflet, security-applications, matchroles]

# Dependency graph
requires:
  - phase: 02-iris-ingestion-pipeline-scoring-classification-telemetry
    provides: PopHeat.Reading / PopHeat.BatchTelemetry persisted tables, insert-only
provides:
  - PopHeat.Reading:LatestPerVenue and PopHeat.Reading:CountsByHeatLevel queries (D-04 single source of truth shared by /venues and /counts)
  - PopHeat.API (%CSP.REST) serving GET /venues, /counts, /telemetry, /status live over port 52773
  - iris/PopHeat/www/dashboard.html minimal Leaflet/OSM page, served at /csp/popheat/dashboard.html
  - docker/init-production.sh registration that makes both web applications publicly reachable with no manual steps on a clean volume
affects: [03-02-dashboard-api, 03-03-dashboard-api]

# Actuals (#2632)
actuals:
  tokens: 16686
  tasks: 2
  commits: 6
  plan_head_before: 7e0de1b

# Tech tracking
tech-stack:
  added: [Leaflet 1.9.4 (CDN, SRI-pinned)]
  patterns:
    - "%CSP.REST dispatch class with Try/Catch-wrapped JSON classmethods"
    - "ROW_NUMBER() OVER (PARTITION BY VenueId ...) WHERE RowNum=1 for latest-per-venue"
    - "Security.Applications MatchRoles=\":<db resource>\" for app-scoped public read access"

key-files:
  created: [iris/PopHeat/API.cls, iris/PopHeat/www/dashboard.html]
  modified: [iris/PopHeat/Reading.cls, docker/init-production.sh]

key-decisions:
  - "The HTTP 403 on /csp/popheat/api/venues was an AUTHORIZATION failure, not an authentication one. AutheEnabled=64 gets an anonymous request past authentication as UnknownUser, but UnknownUser has no read privilege on the database backing POPHEAT -- whose resource is %DB_%DEFAULT in this image, NOT %DB_POPHEAT -- so IRIS could not execute the dispatch class at all. Fixed with MatchRoles=\":<db resource>\" on the application (leading colon = additionally grant this role for requests to THIS application only), which is narrower than granting UnknownUser a global role. The resource name is resolved at runtime via Config.Namespaces -> Config.Databases -> SYS.Database.ResourceName rather than hardcoded."
  - "Resource=\"\" on both applications. The previous attempt's custom PopHeat_Public resource + PopHeatPublic role (and the %Service_WebGateway AutheEnabled widening) are redundant once MatchRoles supplies the needed privilege, and were proven unnecessary by a clean-volume run with both removed. The dashboard/API is a deliberately public, read-only demo view (D-06, dashboard-api.spec R6 -- no login), so an extra application resource gate adds nothing."
  - "The dashboard page is served as dashboard.html, not dashboard.csp (deviation from the plan's literal filename). A .csp extension routes the request to CSP's page-compilation machinery instead of static file serving and 404s under a ServeFiles application; identical bytes at dashboard.html return 200. The page is pure static HTML/JS with zero server-side ObjectScript (D-05), so it never needed CSP compilation. Canonical URL: http://localhost:52773/csp/popheat/dashboard.html."
  - "The /csp/popheat application had no Path property at all (IRIS auto-creates it for the namespace's Interoperability Management Portal because merge.cpf sets Interop=1), so it pointed nowhere and every file under it 404'd regardless of auth. init-production.sh now sets Path explicitly and keeps Modify-or-Create rather than create-if-missing."
  - "Every conditional in init-production.sh's IRIS heredocs is kept on ONE physical line: the iris session terminal executes input line by line, so a multi-line if/else brace block raises <SYNTAX> and both branches then run unconditionally."

patterns-established:
  - "Query LatestPerVenue and CountsByHeatLevel share the textually identical ROW_NUMBER()-partitioned subquery (D-04) -- copy it verbatim for any further latest-per-venue aggregate, do not re-derive."
  - "Every PopHeat.API classmethod wraps its body in Try/Catch, sets %response.ContentType/Status explicitly, and never lets an IRIS %Status error reach the client (T-03-02)."
  - "A public IRIS web application needs BOTH AutheEnabled=64 (authentication) and MatchRoles=\":<db resource>\" (authorization). Setting only the first yields a bare 403 with no diagnostic."

requirements-completed: [DASH-01, DASH-05, DASH-06]
# Note: REQUIREMENTS.md marks DASH-01 and DASH-05 Complete. DASH-06 is also
# declared by Plan 03-02 (the status badge in the UI), so the shared-ID gate
# correctly holds it Pending until 03-02 ships; this plan delivers only its
# API half (GET /status).

coverage:
  - id: D1
    description: "PopHeat.Reading:LatestPerVenue backs GET /venues with the latest reading per venue, ordered by VenueId"
    requirement: DASH-01
    verification:
      - kind: integration
        ref: "curl -sf http://localhost:52773/csp/popheat/api/venues -> HTTP 200, 906 objects with keys venueId/venueName/category/lat/lon/popularity/heatLevel/observedAt, one per venue"
        status: pass
    human_judgment: false
  - id: D2
    description: "PopHeat.Reading:CountsByHeatLevel backs GET /counts from the identical latest-per-venue subquery, always emitting all four levels"
    requirement: DASH-05
    verification:
      - kind: integration
        ref: "curl -sf http://localhost:52773/csp/popheat/api/counts -> {\"BAIXO\":362,\"MEDIO\":99,\"ALTO\":445,\"CRITICO\":0}; CRITICO present at 0, and the three non-zero values sum to the 906 rows /venues returned (D-04 consistency)"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /telemetry returns PopHeat.BatchTelemetry:RecentBatches as camelCase JSON, newest first, capped at 20"
    verification:
      - kind: integration
        ref: "curl -sf http://localhost:52773/csp/popheat/api/telemetry -> HTTP 200, exactly 20 objects with keys readingCount/elapsedSeconds/throughput/recordedAt, recordedAt descending"
        status: pass
    human_judgment: false
  - id: D4
    description: "GET /status reports pipeline state as a boolean, HTTP 200 always, and never gates the other endpoints"
    requirement: DASH-06
    verification:
      - kind: integration
        ref: "curl http://localhost:52773/csp/popheat/api/status -> {\"running\":true} while the production runs; after `iop --stop` it returned {\"running\":false} at HTTP 200 with /venues, /counts and /telemetry still serving 200 (R6 non-gating), then true again after restart"
        status: pass
    human_judgment: false
  - id: D5
    description: "dashboard.html is a static Leaflet/OSM page served publicly that fetches /csp/popheat/api/venues and renders a circleMarker per venue"
    verification:
      - kind: integration
        ref: "curl -sf http://localhost:52773/csp/popheat/dashboard.html -> HTTP 200 and the body matches 'leaflet' (the plan's Task 1 <verify>, EXIT:0)"
        status: pass
    human_judgment: true
    rationale: "The page is now provably served and its markup/JS are provably correct and complete, but nobody has yet LOOKED at the rendered map in a browser -- that tiles load, that markers appear where the venues are, that the CDN SRI hashes do not block Leaflet. Plan 03-02's human-check covers this visual pass."
  - id: D6
    description: "docker/init-production.sh alone makes both web applications reachable on a clean volume, idempotently"
    verification:
      - kind: integration
        ref: "docker compose down -v && up -d && init-production.sh on an empty volume: zero ERROR/<SYNTAX> lines, all five URLs 200; second identical run also zero errors with all five URLs still 200"
        status: pass
    human_judgment: false

# Metrics
duration: 31 min (continuation session; excludes the earlier halted session)
completed: 2026-09-21
status: complete
---

# Phase 3 Plan 1: Dashboard API Summary

**All four read-only REST endpoints (`/venues`, `/counts`, `/telemetry`, `/status`) and the Leaflet dashboard page are live and verified over HTTP from a clean Docker volume, after root-causing the 403 as a missing database-read privilege for `UnknownUser` and the 404 as a pathless web application plus a `.csp` extension that bypasses static file serving.**

## Performance

- **Duration:** 31 min (this continuation session; the earlier halted session is not counted)
- **Started:** 2026-09-21T10:15:00Z
- **Completed:** 2026-09-21T10:46:48Z
- **Tasks:** 2 of 2 (Task 1 repaired and re-verified, Task 2 implemented)
- **Files modified:** 8 (2 created earlier and now fixed/renamed, 2 source files extended, 4 planning docs retargeted)

## Accomplishments

- **Both live-verification failures root-caused and fixed durably.** `/csp/popheat/api/venues` now returns HTTP 200 with real venue JSON and `/csp/popheat/dashboard.html` returns HTTP 200, from a `docker compose down -v` clean volume with `docker/init-production.sh` as the only setup step — the D-05 "no manual intervention" contract the contest demo depends on.
- **403 root cause: authorization, not authentication.** `AutheEnabled=64` admits the anonymous request as `UnknownUser`, but that account had no read privilege on the database backing POPHEAT (resource `%DB_%DEFAULT` in this image — *not* `%DB_POPHEAT`), so IRIS could not execute the dispatch class and answered a bare 403. Fixed with `MatchRoles=":<db resource>"` scoped to each application, with the resource name resolved at runtime rather than hardcoded.
- **404 root cause: two independent defects.** The `/csp/popheat` application had no `Path` property at all (it is auto-created by IRIS for the namespace's Interop Management Portal), and a `.csp` extension is routed to CSP page compilation rather than static file serving. Fixed by setting `Path` and renaming the page to `dashboard.html`.
- **Task 2 shipped:** `PopHeat.Reading:CountsByHeatLevel` (built on the textually identical latest-per-venue subquery, D-04) plus `Counts()`, `Telemetry()` and `Status()` on `PopHeat.API`. `/counts` always emits all four heat levels as integers; `/telemetry` returns 20 newest-first batches; `/status` never propagates an internal error.
- **`/venues` and `/counts` proven consistent live:** `{"BAIXO":362,"MEDIO":99,"ALTO":445,"CRITICO":0}` summed exactly to the 906 objects `/venues` returned in the same run.
- **R6 non-gating behavior proven live:** stopping the production flipped `/status` to `{"running":false}` at HTTP 200 while `/venues`, `/counts` and `/telemetry` kept serving their last-known data at 200.
- **`init-production.sh` re-runs are now a true no-op** (zero `ERROR`/`<SYNTAX>` lines on the second run), which they were not before.

## Task Commits

1. **Task 1 (repair + re-verify): REST + web-app registration + dashboard page reachable** - `f82c1e5` (fix)
2. **Task 2: /counts, /telemetry, /status + CountsByHeatLevel** - `5bf1710` (feat)
3. **Follow-through: retarget phase 03 plans at dashboard.html** - `5edbb7a` (docs)

Task 1's original implementation was committed in the prior session as `a33d8d0`; `f82c1e5` is the repair that makes it actually work.

## Files Created/Modified

- `docker/init-production.sh` - Runtime resolution of the POPHEAT database resource; `MatchRoles`/`Resource`/`Path` corrections on both web applications; removal of the redundant `PopHeat_Public` resource/role and `%Service_WebGateway` blocks; one-line conditionals so re-runs are a genuine no-op
- `iris/PopHeat/www/dashboard.csp` -> `iris/PopHeat/www/dashboard.html` - Renamed (see deviation 1); content unchanged apart from a header comment recording why
- `iris/PopHeat/API.cls` - Added `/counts`, `/telemetry`, `/status` routes and their classmethods
- `iris/PopHeat/Reading.cls` - Added `Query CountsByHeatLevel`
- `.planning/phases/03-dashboard-api/03-01-PLAN.md`, `03-02-PLAN.md`, `03-03-PLAN.md`, `03-PATTERNS.md` - `dashboard.csp` references retargeted at `dashboard.html`

## Decisions Made

See `key-decisions` in frontmatter. In short: authorization (not authentication) was the 403; the fix is an application-scoped `MatchRoles` grant of the namespace's own database role, resolved at runtime; the custom public resource/role and the `%Service_WebGateway` change were removed after a clean-volume run proved them unnecessary; and the dashboard is served as a plain `.html` static file.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed `dashboard.csp` to `dashboard.html`**
- **Found during:** Task 1 re-verification
- **Issue:** The plan specifies `iris/PopHeat/www/dashboard.csp` and the URL `/csp/popheat/dashboard.csp`. A `.csp` extension is handed to CSP's page-compilation machinery rather than the static-file path, so it 404s under a `ServeFiles` application even with a correct `Path` and correct auth. Evidence: identical bytes copied to `dashboard.html` returned HTTP 200 with the correct content while `.csp` kept returning 404.
- **Fix:** `git mv iris/PopHeat/www/dashboard.csp iris/PopHeat/www/dashboard.html`. The page is pure static HTML/JS with zero server-side ObjectScript (D-05 — "single static HTML page (vanilla JS + Leaflet via CDN)"), so it never required CSP compilation. All references updated: `docker/init-production.sh`, and the `dashboard.csp` paths/URLs in `03-01-PLAN.md`, `03-02-PLAN.md`, `03-03-PLAN.md` and `03-PATTERNS.md` (Plans 03-02/03-03 grep that file by path and open it by URL, so leaving them stale would have broken both).
- **Files modified:** `iris/PopHeat/www/dashboard.html` (renamed), `docker/init-production.sh`, 4 planning docs
- **Verification:** `curl -sf http://localhost:52773/csp/popheat/dashboard.html | grep -qi leaflet` -> EXIT:0 on a clean volume
- **Committed in:** `f82c1e5`, `5edbb7a`

**2. [Rule 1 - Bug] Replaced the `PopHeat_Public` resource/role and `%Service_WebGateway` changes with an application-scoped `MatchRoles` grant**
- **Found during:** Task 1 re-verification
- **Issue:** The prior session's `AutheEnabled=64` + `PopHeat_Public` resource + `PopHeatPublic` role for `UnknownUser` + `%Service_WebGateway` widening got requests past authentication but not past authorization — `UnknownUser` still had no read on the POPHEAT database's resource, so the dispatch class could not execute (403).
- **Fix:** `MatchRoles=":<db resource>"` and `Resource=""` on both applications, with the resource name resolved at runtime through `Config.Namespaces` -> `Config.Databases` -> `SYS.Database.ResourceName` (it is `%DB_%DEFAULT` here, not `%DB_POPHEAT`, so hardcoding would have been wrong). The now-redundant `PopHeat_Public` resource, `PopHeatPublic` role, the `UnknownUser` role grant and the `%Service_WebGateway` `AutheEnabled` change were all removed — a clean-volume run with none of them present serves every endpoint at 200, so none was ever necessary.
- **Files modified:** `docker/init-production.sh`
- **Verification:** Clean-volume run: `/csp/popheat/api/venues` 200 with real venue JSON; the script no longer touches any system service or global role
- **Committed in:** `f82c1e5`

**3. [Rule 1 - Bug] Set a `Path` on the `/csp/popheat` application**
- **Found during:** Task 1 re-verification
- **Issue:** The application had no `Path` property at all, so it pointed nowhere and every file under it 404'd no matter what its auth settings said. The prior summary reported `Path` as correct; it was not set.
- **Fix:** `set props2("Path") = "${APP_DIR}/iris/PopHeat/www/"` alongside `ServeFiles=1`.
- **Files modified:** `docker/init-production.sh`
- **Verification:** `/csp/popheat/dashboard.html` -> HTTP 200 on a clean volume
- **Committed in:** `f82c1e5`

**4. [Rule 1 - Bug] One-line conditionals in the IRIS heredocs**
- **Found during:** Task 1 re-verification (second `init-production.sh` run)
- **Issue:** The `iris session` terminal executes its input line by line, so the multi-line `if "$X" = "1" { ... } else { ... }` Modify-or-Create blocks raised `<SYNTAX>` on every brace line and then ran BOTH branches unconditionally. Re-running the script printed `ERROR #867: Cannot create application ... already exists` — the idempotency the plan requires was accidental, not real.
- **Fix:** Every conditional is now a single physical line, and the existence check moved into ObjectScript (`if ##class(Security.Applications).Exists(...) { Modify } else { Create }`), dropping the fragile shell-side marker grep entirely. Same treatment for the database-resource resolution block.
- **Files modified:** `docker/init-production.sh`
- **Verification:** Second consecutive run on the clean volume: 0 lines matching `ERROR|<SYNTAX>`, all five URLs still 200
- **Committed in:** `f82c1e5`

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 bugs).
**Impact on plan:** All four were required to make the plan's own `<verify>` commands pass. Deviation 1 changes a filename and URL the plan hardcodes — every dependent reference was updated in the same pass, and the new canonical dashboard URL is `http://localhost:52773/csp/popheat/dashboard.html`. Deviation 2 *reduces* the security surface relative to the prior session (no system-service change, no global role granted to `UnknownUser`). No scope creep.

## Issues Encountered

- The prior session's diagnosis chased authentication (service-level auth bitmasks, CSRF, cookies, container restarts) when the failure was authorization. Recorded here so it is not repeated: a bare 403 with no `WWW-Authenticate` header on an `AutheEnabled=64` IRIS application means the anonymous user lacks a *privilege*, most often read on the namespace's database resource.
- `iop --stop PopHeat.Production` rejects the production name as an unrecognized argument; `iop --stop` with `IRISNAMESPACE=POPHEAT` in the environment is the working form. Worth knowing for the demo runbook.
- `CRITICO` was 0 in every sample taken during this session. That is the synthetic popularity model's output for this time of day, not an API defect — `/counts` correctly emits the key with a 0 value, which is exactly the behavior the plan requires.

## User Setup Required

None. A clean `docker compose up -d` followed by `docker compose exec -T iris sh /irisdev/app/docker/init-production.sh` yields working endpoints with no manual steps, verified from an empty volume. Note that `data/venues.json` (gitignored) must exist in the repo root for the pipeline to persist readings — regenerate with `python3 scripts/build_catalog.py --config config/catalog_build.json`.

## Next Phase Readiness

**Ready for Plan 03-02.** The full vertical slice is proven live: public HTTP -> `%CSP.REST` dispatch -> embedded SQL over Phase 2's tables -> JSON -> a served page that fetches it. Plan 03-02 extends `iris/PopHeat/www/dashboard.html` (note the extension) against the now-stable four-endpoint contract; its `grep`-based `<verify>` commands and human-check URLs have already been retargeted at that filename.

Open item for 03-02's human-check: nobody has yet viewed the rendered map in a browser (tiles loading, marker placement, CDN SRI hashes not blocking Leaflet) — the page is proven *served*, not proven *pretty*.

---
*Phase: 03-dashboard-api*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: iris/PopHeat/API.cls
- FOUND: iris/PopHeat/Reading.cls
- FOUND: iris/PopHeat/www/dashboard.html
- FOUND: docker/init-production.sh
- FOUND: commit f82c1e5 (fix), 5bf1710 (feat), 5edbb7a (docs)
- VERIFIED LIVE: Task 1 `<verify>` EXIT:0, Task 2 `<verify>` EXIT:0, both against a clean-volume stack
