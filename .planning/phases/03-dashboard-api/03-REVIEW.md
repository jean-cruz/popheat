---
phase: 03-dashboard-api
reviewed: 2026-09-21T00:00:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - .gitignore
  - docker/init-production.sh
  - iris/PopHeat/API.cls
  - iris/PopHeat/Reading.cls
  - iris/PopHeat/www/dashboard.html
  - specs/dashboard-api.spec
  - specs/heat-classification.spec
  - specs/ingestion-pipeline.spec
  - specs/popularity-model.spec
  - specs/telemetry.spec
  - specs/venue-sourcing.spec
findings:
  critical: 0
  warning: 6
  info: 4
  total: 10
status: issues_found
---

# Phase 3: Code Review Report

**Reviewed:** 2026-09-21T00:00:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

Reviewed the Phase 3 deliverables (`iris/PopHeat/API.cls`, `iris/PopHeat/Reading.cls`,
`docker/init-production.sh`, `iris/PopHeat/www/dashboard.html`) at standard depth, plus a
light pass over the five `*.spec` files and `.gitignore`, which landed in this diff
incidentally per the task framing and contain nothing requiring action.

No injection vectors, hardcoded secrets, or crashing null-derefs were found — the SQL is
fixed and parameterless as documented, XSS is guarded by `escapeHtml` for OSM-derived
strings, and every REST method has a catch-all that degrades to a generic 500 without
leaking internals. There are no Critical findings.

The findings below are mostly setup-script robustness gaps and defense-in-depth/data-
integrity items that don't currently manifest as observable bugs but are worth fixing
given the project's stated single point of failure: a working live demo on a one-day
timeline. The most consequential are: `docker/init-production.sh` silently swallowing a
genuine `iop --start` failure behind a message that assumes only "already running", the
unpinned pip dependencies in that same script, and the hard runtime dependency on an
external CDN (unpkg.com) for the map to render at all. The `LatestPerVenue` /
`CountsByHeatLevel` queries duplicate the same subquery text in two places despite a
comment claiming they "can never drift apart" — nothing enforces that today.

## Warnings

### WR-01: `iop --start` failure is masked as "already running"

**File:** `docker/init-production.sh:149-150`
**Issue:** `iop --start PopHeat.Production --detach || echo "(already running -- ok on re-run)"` treats *any* non-zero exit from `iop --start` as the benign "already running" case and continues on to print `"=== PopHeat: init complete ==="`. If the production genuinely fails to start (bad settings.py migration, missing IOP class, port conflict, etc.), the script reports success anyway, which is exactly the failure mode most damaging to a same-day live demo: setup appears to finish cleanly while the ingestion pipeline never actually starts.
**Fix:** Distinguish the two cases, e.g. capture stderr and only suppress when it matches an "already running" message, or check `iop --status` afterward and fail loudly if the production isn't actually running:
```sh
if ! iop --start PopHeat.Production --detach; then
  iop --status | grep -qi "PopHeat.Production.*running" || { echo "FATAL: PopHeat.Production failed to start"; exit 1; }
  echo "(already running -- ok on re-run)"
fi
```

### WR-02: Unpinned pip dependencies in a one-shot setup script

**File:** `docker/init-production.sh:21`
**Issue:** `pip3 install --quiet iris-pex-embedded-python tzdata` installs whatever the latest published versions are, with no version pin. Given the project's one-day timeline and "if the demo isn't running, nothing else matters" priority, an unrelated upstream release between now and the contest run (or a rebuild of the container) could silently change PEX behavior or break compatibility with the installed IRIS version.
**Fix:** Pin explicit versions once a known-good combination is confirmed, e.g. `pip3 install --quiet iris-pex-embedded-python==<version> tzdata==<version>`.

### WR-03: Dashboard has a hard, unmitigated dependency on an external CDN

**File:** `iris/PopHeat/www/dashboard.html:32-34,386-391`
**Issue:** Leaflet CSS/JS and leaflet.heat are loaded exclusively from `unpkg.com` with no local fallback. SRI + `crossorigin` correctly guards against tampering, but there is no fallback if unpkg is unreachable (venue network restrictions, CDN outage, no internet at demo time) — the map (the dashboard's entire purpose) would fail to render at all, with no degraded-but-functional path.
**Fix:** Vendor Leaflet/leaflet.heat as local static assets served alongside `dashboard.html` (the `/csp/popheat` static app already serves this directory), or at minimum add a local fallback `<script>` that loads a vendored copy on CDN failure.

### WR-04: `LatestPerVenue` and `CountsByHeatLevel` duplicate the same subquery text

**File:** `iris/PopHeat/Reading.cls:44-49,61-67`
**Issue:** Both queries independently repeat the identical `ROW_NUMBER() OVER (PARTITION BY VenueId ORDER BY ObservedAt DESC, ID DESC) ... WHERE RowNum = 1` subquery. The class comments assert this makes the two "textually identical" so the map and counts panel "can never drift apart" (D-04) — but that guarantee is purely a documentation convention, not an enforced one. Editing the tie-break rule or the partition key in one query and forgetting the other silently reintroduces the drift the design explicitly set out to prevent.
**Fix:** There's no native way to share a `%SQLQuery` body across two class queries, but a comment alone doesn't prevent drift; consider a single tested helper query/view (e.g. a `%SQLQuery(CONTAINID)` view class or materializing "latest per venue" as an actual persistent projection) that both queries select from, or at minimum a regression test asserting the two subquery bodies are byte-identical so a future edit to one without the other fails CI.

### WR-05: Unauthenticated DB-resource fallback could grant a broader role than intended

**File:** `docker/init-production.sh:58-73,101-102`
**Issue:** When the dynamic resolution of the POPHEAT database's resource name fails, the script falls back to `DB_RESOURCE="%DB_%DEFAULT"` and grants that role to `UnknownUser` (scoped to this one application) via `MatchRoles=":${DB_RESOURCE}"`. `%DB_%DEFAULT` is commonly the resource backing the IRIS instance's default/system database, which in many installs is shared by other namespaces. Falling back to it silently (only a printed warning, script continues) changes the unauthenticated access footprint from "read POPHEAT's own data" to "whatever `%DB_%DEFAULT`'s role permits", without failing the setup or requiring confirmation. The actual exploitable surface is still bounded by `PopHeat.API`'s fixed route set, so this isn't remotely-exploitable today, but it's a silent privilege-scope change that a security reviewer should not have to infer from a fallback branch.
**Fix:** Treat resolution failure as fatal (or clearly loud) rather than silently substituting a different, broader resource:
```sh
if [ -z "$DB_RESOURCE" ]; then
  echo "FATAL: could not resolve ${IRIS_NAMESPACE} database resource -- refusing to grant a fallback role" >&2
  exit 1
fi
```

### WR-06: API JSON responses don't pin an explicit UTF-8 charset, in a codebase that already hit this exact issue once

**File:** `iris/PopHeat/API.cls:26,60,87` (compare `iris/PopHeat/www/dashboard.html:470-476`)
**Issue:** `dashboard.html` documents, with a specific in-code war story, that this same IRIS instance/web-app family serves static content as `Content-Type: text/html; charset=ISO-8859-1` by default, overriding the page's own `<meta charset="UTF-8">`. `API.cls` sets `%response.ContentType = "application/json"` on every route but never pins a charset (e.g. `"application/json; charset=utf-8"` or `Set %response.CharSet = "utf-8"`). Venue names and categories sourced from OpenStreetMap for a Porto-area catalog will routinely contain accented Portuguese characters (é, ã, ç, ô). The dashboard.html comment reasons that `response.json()` always UTF-8-decodes regardless of headers (true, per the Fetch spec) — but that only saves the day if IRIS actually *writes* UTF-8 bytes on the wire; if this CSP application's default output encoding matches the one already observed to default to ISO-8859-1 for the sibling static app, the bytes themselves would be wrong and no amount of client-side UTF-8 decoding fixes already-mis-encoded bytes.
**Fix:** Pin the charset explicitly rather than relying on the application/namespace default, e.g. `Set %response.ContentType = "application/json; charset=utf-8"` (or `Set %response.CharSet = "utf-8"`) in each of `Venues()`, `Counts()`, `Telemetry()`, `Status()`, and verify against a venue name containing an accented character before the demo.

## Info

### IN-01: Unexpected `HeatLevel` values are silently dropped from `/counts` with no diagnostic

**File:** `iris/PopHeat/API.cls:64-71`
**Issue:** If a persisted `HeatLevel` value is ever anything other than the four canonical strings (e.g. a casing mismatch introduced upstream), `Counts()` silently skips it rather than logging or surfacing it — the venue simply disappears from every bucket's total with no trace. This is defensible as a strict "never add a fifth key" contract, but combined with `Reading.HeatLevel` having no schema-level enum constraint (see IN-02), a future data-quality regression in the ingestion pipeline would be invisible from the API/dashboard side.
**Fix:** Consider a debug-log line (or a telemetry counter) when a row is skipped, so a classification regression is discoverable without querying the underlying table directly.

### IN-02: `Reading.Popularity` and `Reading.HeatLevel` have no schema-level range/enum constraints

**File:** `iris/PopHeat/Reading.cls:19-24`
**Issue:** The class comments document `Popularity` as constrained to `[0.02, 0.98]` (POPU-01) and `HeatLevel` as one of exactly four strings (HEAT-01/02), but neither is enforced by the class definition (no `MINVAL`/`MAXVAL` on `Popularity`, no `VALUELIST` on `HeatLevel`). Enforcement today relies entirely on the ingestion pipeline (Phase 2, out of this review's scope) behaving correctly; the persistence layer itself would silently accept an out-of-range or misspelled value.
**Fix:** Add `Property Popularity As %Numeric(SCALE = 3, MINVAL = 0.02, MAXVAL = 0.98);` and `Property HeatLevel As %String(MAXLEN = 20, VALUELIST = ",BAIXO,MEDIO,ALTO,CRITICO");` (or equivalent) so a future insert-path bug fails fast at persistence instead of silently reaching the API and dashboard.

### IN-03: Dynamic-object literal parens auto-type-infers string-typed fields, risking a purely-numeric venue name serializing as a JSON number

**File:** `iris/PopHeat/API.cls:31-40,92-97`
**Issue:** `Venues()`/`Telemetry()` build response fields with `{"venueName": (result.Get("VenueName")), ...}` — bare-parens literal syntax, which IRIS auto-types as a JSON number whenever the runtime value is a canonical number and as a string otherwise, with no explicit type hint (contrast `Counts()`, which explicitly passes `"number"` to `%Set`). A venue whose OSM name is purely numeric (not implausible for a numbered venue/address-style name) would serialize `venueName` as a JSON number instead of a string, which the client happens to tolerate (`escapeHtml`/`String(...)` coerces it back), but it's an inconsistent, undocumented wire contract that a stricter future API consumer would not tolerate.
**Fix:** Force the string-typed fields explicitly, e.g. `"venueName": (result.Get("VenueName")):%String` or build with `%Set(..., "string")`, so the JSON type of a string column never depends on the incidental content of the value.

### IN-04: `%ResultSet` instances are never explicitly closed

**File:** `iris/PopHeat/API.cls:27,62,88`
**Issue:** `Venues()`, `Counts()`, and `Telemetry()` each create a `%ResultSet` via `##class(%ResultSet).%New(...)` and never call `.Close()` (or otherwise release it) once done, relying entirely on garbage collection at method-scope exit. Not a functional bug given IRIS's `%ResultSet` lifecycle, but explicit cleanup is the more defensive/conventional pattern for statement handles and one exception path (an error thrown mid-loop) leaves the open cursor to the GC in every case.
**Fix:** Add `Do result.Close()` after the loop (and consider closing in the catch path too) for symmetry, though this is low priority given IRIS's normal handle GC.

---

_Reviewed: 2026-09-21T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
