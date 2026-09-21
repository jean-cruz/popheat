---
phase: 03-dashboard-api
plan: 02
subsystem: frontend
tags: [leaflet, leaflet-heat, vanilla-js, static-html, sri, ui-spec, dashboard]

# Dependency graph
requires:
  - phase: 03-dashboard-api
    plan: 01
    provides: PopHeat.API serving GET /venues, /counts, /telemetry, /status; the static dashboard.html page and its public web-application registration
provides:
  - Weighted Leaflet.heat layer over every venue with a reading (R2/DASH-02), min weight 0.15
  - ALTO/CRITICO-only circleMarkers with severity-proportional radii and 240px-wrapping popups (R3/DASH-03, R4/DASH-04)
  - Fixed 56px top bar with a non-gating pipeline status badge (R6/DASH-06)
  - Floating counts panel (R5/DASH-05) and telemetry panel, fully styled to 03-UI-SPEC.md
  - renderHeatLayer/renderMarkers/renderCounts/renderTelemetry/renderStatus + loadAll(), all idempotent and re-callable -- the seam Plan 03-03's 10s poll plugs into
affects: [03-03-dashboard-api]

# Actuals (#2632)
actuals:
  tokens: 5383
  tasks: 2
  commits: 3
  plan_head_before: 306345e35efea2a66ed770c33d198de7ab265846
# `commits: 3` is measured as `git rev-list --count 306345e..HEAD` INCLUDING this
# SUMMARY's own docs commit, so the same command re-run after the fact reproduces
# the number. The two production commits are e24baae and 17f666a.
# `tokens` is chars/4 over the realized 21,530-char diff (estimate was 9,000).

# Tech tracking
tech-stack:
  added: ["Leaflet.heat 0.2.0 (CDN, SRI-pinned sha384)"]
  patterns:
    - "Outer-scope layer handles (heatLayer / markerLayer) + remove-then-readd, so every render function is idempotent and safe to call on a timer"
    - "requireOkJson as the first .then() of every fetch, so a non-2xx JSON error body can never be rendered as data"
    - "Per-endpoint independent fetches -- one failing endpoint never blanks the others (R6 non-gating, generalized)"
    - "Pure-ASCII HTML source with String.fromCharCode/HTML entities for non-ASCII glyphs, because IRIS serves this app's static files as ISO-8859-1"

key-files:
  created: []
  modified: [iris/PopHeat/www/dashboard.html]

key-decisions:
  - "The heat layer is given an explicit `gradient` keyed to the four locked D-02 colors (#2ECC71/#F1C40F/#E67E22/#E74C3C) rather than Leaflet.heat's default blue-to-red ramp. Without this the glow and the individual markers would read as two unrelated color scales on the same map. radius/blur/minOpacity stay at near-default values (25/18/0.3) per 03-UI-SPEC.md's 'plugin defaults unless they visibly clash'."
  - "IRIS serves /csp/popheat static files with `Content-Type: text/html; charset=ISO-8859-1`, and an HTTP charset header OVERRIDES <meta charset=\"UTF-8\">. The in-scope fix is to keep dashboard.html pure ASCII (non-ASCII glyphs via String.fromCharCode or HTML entities) rather than change the web-application's charset, which lives in docker/init-production.sh -- outside this plan's declared files. Data from the REST API is unaffected: response.json() always decodes as UTF-8 regardless of the page's own charset, which is why accented venue names render correctly in popups."
  - "An author `display` rule outranks the UA stylesheet's `[hidden] { display: none }`. #counts-rows needed a companion `#counts-rows[hidden] { display: none; }` or its four placeholder zeros showed through the loading placeholder and read as real counts before the first fetch -- the exact opposite of the loading backstop."
  - "Three prohibition-driven copy additions were made beyond the literal task text, all inside 03-UI-SPEC.md's spirit rather than contradicting its locked strings: a top-bar subtitle 'Synthetic crowdedness estimates - not measured crowd counts' (DASH-02 transparency), a popup note 'Estimated crowdedness, not a safety warning.' (DASH-04), and a title attribute on the badge stating it reports the ingestion pipeline, not venue opening hours (DASH-06). None replaces or alters a locked string."
  - "loadAll() fetches the four endpoints independently instead of chaining them, so Plan 03-03 can wrap exactly this function in its 10s interval and attach its stale-data banner to individual rejections without restructuring anything."

patterns-established:
  - "Every render function clears/removes its own previous output first (markerLayer.clearLayers(), map.removeLayer(heatLayer)). Plan 03-03 can call loadAll() on a timer with no leak and no stale state -- do not add a second layer-tracking mechanism."
  - "KEEP dashboard.html PURE ASCII. Verify with `grep -P '[^\\x00-\\x7F]' iris/PopHeat/www/dashboard.html` returning nothing. Plan 03-03's locked banner copy 'Unable to refresh -- showing last known data as of {time}' contains an EM DASH and will mojibake unless written as &mdash; or String.fromCharCode(8212)."
  - "renderStatus() touches only the badge DOM. Any future status handling must preserve that: D-06's non-gating rule is enforced structurally, not by convention."

requirements-completed: [DASH-02, DASH-03, DASH-04, DASH-06]

coverage:
  - id: D1
    description: "Heat layer renders one weighted point per venue with a reading, floored at MIN_HEAT_WEIGHT=0.15 (R2/DASH-02)"
    requirement: DASH-02
    verification:
      - kind: integration
        ref: "Headless Chrome against the live stack: heat glow renders over the whole venue area (screenshot). Boundary values proven in-browser via a synthetic BAIXO/MEDIO/ALTO/CRITICO set -- weights emitted were 0.97, 0.6, 0.3, 0.15, i.e. 0.02 clamped up to 0.15 and 0.98-class values passed through unrounded"
        status: pass
      - kind: command
        ref: "grep -q 'L.heatLayer' && grep -q 'MIN_HEAT_WEIGHT' iris/PopHeat/www/dashboard.html -> EXIT:0"
        status: pass
    human_judgment: false
  - id: D2
    description: "Individual circleMarkers are restricted to ALTO/CRITICO venues, CRITICO strictly larger than ALTO, additive to the heat layer (R3/DASH-03, R4/DASH-04)"
    requirement: DASH-03
    verification:
      - kind: integration
        ref: "Live page: 506-519 markers rendered, every one at radius 10 (all ALTO; CRITICO was 0 venues in every sample). Driving renderMarkers() with a synthetic 4-level set produced EXACTLY two markers -- '10:#E67E22 14:#E74C3C' -- with BAIXO/MEDIO contributing none, and the screenshot shows the red CRITICO circle visibly larger than the orange ALTO one"
        status: pass
    human_judgment: false
  - id: D3
    description: "Marker popups follow the 03-UI-SPEC.md copy contract and wrap long venue names inside a 240px content area instead of truncating"
    requirement: DASH-04
    verification:
      - kind: integration
        ref: "Popup opened in-browser on the longest ALTO venue name in the live catalog ('Sabores da Invicta - Confeitaria, Restaurante, Salao de Cha'): the name wrapped onto two lines inside the box, followed by 'restaurant - ALTO' in the ALTO orange, 'Popularity: 0.647', and 'as of 12:02:49' in accent blue. No ellipsis, no overflow"
        status: pass
    human_judgment: false
  - id: D4
    description: "Counts panel renders four rows sourced from /counts, Display-size digits colored per heat level, and those numbers match the latest-reading-per-venue rule (R5/DASH-05)"
    verification:
      - kind: integration
        ref: "Live SQL cross-check at the same moment as the page load: `SELECT HeatLevel, COUNT(*) ... ROW_NUMBER() OVER (PARTITION BY VenueId ...) WHERE RowNum=1 GROUP BY HeatLevel` returned ALTO 518 / BAIXO 336 / MEDIO 52 (no CRITICO row) and /counts returned {\"BAIXO\":336,\"MEDIO\":52,\"ALTO\":518,\"CRITICO\":0}. Independently, deriving the distribution from the 906 objects /venues returned matched /counts exactly and summed to 906"
        status: pass
      - kind: integration
        ref: "Computed styles read from the live DOM: count digit 28px/600 colored rgb(46,204,113)=#2ECC71 for BAIXO, label 13px/600, panel background rgb(31,41,51)=#1F2933, padding 24px"
        status: pass
    human_judgment: false
  - id: D5
    description: "Status badge reports pipeline state without ever gating the venue/heat/counts/telemetry data (R6/DASH-06)"
    requirement: DASH-06
    verification:
      - kind: integration
        ref: "Production actually stopped via `iop --stop` (IRISNAMESPACE=POPHEAT): /status flipped to {\"running\":false} and the reloaded page showed a hollow gray dot + 'Pipeline: Stopped' while the map, heat layer, 516 markers, counts (346/44/516/0 = 906) and telemetry all kept showing last-persisted data unchanged. Production restarted afterwards; /status back to {\"running\":true} and the badge back to a filled #3B82F6 dot + 'Pipeline: Running'"
        status: pass
    human_judgment: false
  - id: D6
    description: "Telemetry panel renders the newest batch's reading count, elapsed seconds, throughput and recorded time from /telemetry's first element"
    verification:
      - kind: integration
        ref: "Live page rendered 'Last batch: 150 readings - 0,003s - 43.249/s' and 'Recorded 12:19:47', matching /telemetry's first (newest) element"
        status: pass
    human_judgment: false
  - id: D7
    description: "Loading, status-failure and empty-telemetry backstops behave as 03-UI-SPEC.md specifies"
    verification:
      - kind: integration
        ref: "In-browser probe patching window.fetch before DOMContentLoaded: /status hard-rejected, /counts left unresolved, /telemetry returned []. Result -- badge 'Pipeline: Stopped' with border rgb(154,165,177) and transparent fill; countsPlaceholderHidden=false and countsRowsHidden=true (placeholder only, no fabricated zeros); telemetry kept its placeholder; 515 markers + heat layer still rendered from the untouched /venues; jsErrors=0"
        status: pass
    human_judgment: false
  - id: D8
    description: "Every CDN script/link tag carries a Subresource Integrity hash plus crossorigin=anonymous (T-03-06)"
    verification:
      - kind: command
        ref: "3 CDN tags, 3 integrity=\"sha384-\", 3 crossorigin=\"anonymous\". Hashes computed from the exact pinned files; the leaflet.css/leaflet.js downloads reproduced Leaflet's published sha256 SRI byte-for-byte, and headless Chrome executed both plus leaflet-heat without an integrity failure (the map renders)"
        status: pass
    human_judgment: false
  - id: D9
    description: "Overall visual fidelity to 03-UI-SPEC.md as a judge would see it on demo day"
    verification:
      - kind: integration
        ref: "Five headless-Chrome screenshots reviewed (normal, loading/degraded, production-stopped, popup open, synthetic marker sizing) plus computed-style assertions for every locked token"
        status: pass
    human_judgment: true
    rationale: "Computed styles, copy, colors and geometry were each asserted mechanically against the locked contract, and the rendered output was visually inspected in headless Chrome at several viewport sizes. What remains genuinely judgment-bound is aesthetic adequacy on a real display -- notably whether the heat layer's radius/blur reads well at the demo's chosen zoom when ~520 ALTO markers overlap in the historic centre. 03-UI-SPEC.md accepts that overlap as a backstop; a human should still confirm it looks right on the actual demo screen."

# Metrics
duration: 34 min
completed: 2026-09-21
status: complete
---

# Phase 3 Plan 2: Dashboard Visual Contract Summary

**The dashboard is now the product rather than plumbing: a D-02-gradient heat layer over all 906 venues, ALTO/CRITICO-only markers sized by severity with wrapping popups, and a fully styled top bar, counts panel and telemetry panel — every locked 03-UI-SPEC.md token asserted against the live DOM and every state (normal, loading, status-failure, pipeline-stopped) verified in a real browser.**

## Performance

- **Duration:** 34 min
- **Started:** 2026-09-21T10:52:11Z
- **Completed:** 2026-09-21T11:26:17Z
- **Tasks:** 2 of 2
- **Files modified:** 1 (`iris/PopHeat/www/dashboard.html`, +477/−18)

## Accomplishments

- **The open item 03-01 left behind is now closed.** 03-01 could only prove the page was *served*; nobody had looked at it. This plan rendered it in headless Chrome: OSM tiles load, both Leaflet bundles execute (so the CDN SRI hashes do **not** block them), and the map draws. The heat layer, markers, popups and panels were each verified against the running stack, not inferred from source.
- **Heat layer (R2/DASH-02) with a proven floor.** One point per venue, weight `Math.max(popularity, 0.15)`, no client-side rounding. Both boundary cases were exercised in-browser: a 0.02-popularity venue emits 0.15, a 0.97 venue emits 0.97 unchanged.
- **Markers (R3/DASH-03, R4/DASH-04) proven exclusive and proven ordered.** Live, all ~515 markers were radius-10 ALTO. Because CRITICO was 0 venues in every sample this session, the CRITICO branch was exercised by driving `renderMarkers()` with a synthetic four-level set: exactly two markers came out — `14:#E74C3C` and `10:#E67E22` — with BAIXO/MEDIO contributing none.
- **Counts panel (R5/DASH-05) cross-checked against SQL, not just against itself.** A direct `ROW_NUMBER() OVER (PARTITION BY VenueId ...)` query in the container returned ALTO 518 / BAIXO 336 / MEDIO 52 at the same moment `/counts` returned `{"BAIXO":336,"MEDIO":52,"ALTO":518,"CRITICO":0}`, and the per-venue distribution derived from `/venues` matched both and summed to 906.
- **D-06 non-gating proven by actually stopping the pipeline.** With `PopHeat.Production` stopped, the badge went hollow-gray "Pipeline: Stopped" while the map, heat layer, 516 markers, counts and telemetry all kept rendering last-persisted data unchanged. Production was restarted before finishing.
- **All three 03-UI-SPEC.md backstops verified, not assumed.** A probe patching `window.fetch` before `DOMContentLoaded` forced `/status` to reject, `/counts` to hang and `/telemetry` to return `[]`. The badge degraded to "Pipeline: Stopped", the counts panel held its "Loading live data…" placeholder, the telemetry panel held its own, the map still rendered from the untouched `/venues`, and **zero** JS errors were raised.
- **Every locked token asserted mechanically.** Read back from the live DOM: top bar 56px, title 20px/600, label 13px/600, count digit 28px/600 in `#2ECC71`, panel background `#1F2933`, panel padding 24px, counts→telemetry gap 32px, body 16px/400/1.5, running dot `rgb(59,130,246)` = `#3B82F6`.

## Task Commits

1. **Task 1: heat layer + ALTO/CRITICO markers + popups + SRI** — `e24baae` (feat)
2. **Task 2: top bar, status badge, counts panel, telemetry panel, full styling** — `17f666a` (feat)

## Decisions Made

See `key-decisions` in frontmatter. In short: the heat layer gets an explicit gradient keyed to D-02's four colors so glow and markers read as one scale; the page is kept pure ASCII because IRIS serves it as ISO-8859-1; `#counts-rows[hidden]` is required because an author `display` rule beats the UA `[hidden]` rule; three prohibition-driven copy additions were made without altering any locked string; and `loadAll()` is structured as the exact seam Plan 03-03's timer plugs into.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Page served as ISO-8859-1 mojibaked every non-ASCII character in the source**

- **Found during:** Task 2, first live screenshot
- **Issue:** The telemetry line rendered as `Last batch: 150 readings Â· 0,004s Â· 40.800/s`. `curl -D -` showed `Content-Type: text/html; charset=ISO-8859-1` — and an HTTP charset header **overrides** `<meta charset="UTF-8">`, so every UTF-8 byte pair in the file was decoded as two Latin-1 characters. (Two `·` separators and an `é` in a comment were the only non-ASCII bytes; `&middot;` entities elsewhere were unaffected because they are ASCII in the source.)
- **Fix:** Made `dashboard.html` pure ASCII — `const MIDDOT = String.fromCharCode(183)` for the separators, plain `Se` in the comment — with a prominent code comment recording the constraint. Deliberately did **not** change the web application's charset: that lives in `docker/init-production.sh`, outside this plan's declared `files_modified`, and the ASCII-only source is correct regardless of the server setting. Recorded in `.planning/WINDOWS.md` so it stays visible.
- **Files modified:** `iris/PopHeat/www/dashboard.html`
- **Verification:** `grep -P '[^\x00-\x7F]' iris/PopHeat/www/dashboard.html` → no matches; re-rendered screenshot shows `Last batch: 150 readings · 0,004s · 41.962/s` correctly
- **Committed in:** `17f666a`

**2. [Rule 1 - Bug] Loading placeholder leaked four fabricated zeros**

- **Found during:** Task 2, degraded-state probe
- **Issue:** With `/counts` unresolved, the counts panel showed the "Loading live data…" placeholder **and**, underneath it, `0 BAIXO / 0 MEDIO / 0 ALTO / 0 CRITICO`. The `hidden` attribute was set correctly (`countsRowsHidden=true` in the DOM) but had no effect: the author rule `#counts-rows { display: flex }` outranks the UA stylesheet's `[hidden] { display: none }`. Pre-fetch zeros presented as real counts is precisely what the loading backstop exists to prevent.
- **Fix:** Added `#counts-rows[hidden] { display: none; }` plus a comment explaining the specificity trap for any future `hidden`-toggled element that also carries an author `display` rule.
- **Files modified:** `iris/PopHeat/www/dashboard.html`
- **Verification:** Re-ran the probe — `countsRowsHidden=true` and the screenshot now shows the placeholder alone; the normal-state screenshot still shows all four populated rows
- **Committed in:** `17f666a`

### Intentional Additions

**3. [Rule 2 - Compliance] Three copy additions satisfying the plan's own prohibitions**

- **Found during:** Task 2
- **Issue:** The plan carries three `prohibitions` (DASH-02 transparency, DASH-04 values, DASH-06 transparency) that no element in the locked copy contract addressed: nothing on screen said the popularity score is synthetic, nothing stopped CRITICO from reading as a hazard warning, and nothing tied the status badge to the ingestion system rather than a venue's hours.
- **Fix:** Top-bar subtitle "Synthetic crowdedness estimates · not measured crowd counts"; popup note "Estimated crowdedness, not a safety warning."; `title` attribute plus `role="status"` on the badge stating it reports the PopHeat ingestion pipeline, not any venue's opening hours. All three are **additions** — no locked string was replaced or altered.
- **Files modified:** `iris/PopHeat/www/dashboard.html`
- **Verification:** Visible in the rendered screenshots; top bar still measures exactly 56px with the subtitle present
- **Committed in:** `17f666a`

**4. [Rule 2 - Security] HTML-escaping of OSM-sourced strings**

- **Found during:** Task 1
- **Issue:** Popup HTML is built by string concatenation from `venueName`/`category`/`popularity`, which originate in OpenStreetMap — data outside this application's control. Unescaped interpolation is a stored-XSS path the threat model does not cover.
- **Fix:** Added `escapeHtml()` and applied it to every interpolated value in `buildPopupHtml()`.
- **Files modified:** `iris/PopHeat/www/dashboard.html`
- **Verification:** Accented/punctuated real venue names (e.g. "Sabores da Invicta - Confeitaria, Restaurante, Salão de Chá") render correctly in the live popup
- **Committed in:** `e24baae`

**5. [Rule 3 - Blocking] `fetchJson()` helper refactored to literal `fetch(API_BASE + '/…')` call sites**

- **Found during:** Task 2 verification
- **Issue:** The first implementation routed all four calls through `fetchJson(path)`. That is functionally fine but the plan's `key_links` contract declares the pattern `fetch\(.*(counts|telemetry|status)` — which `fetchJson('/counts')` does not match, so the declared integration link would not have been verifiable.
- **Fix:** Replaced the wrapper with `requireOkJson(response)` used as the first `.then()` of four explicit `fetch(API_BASE + '/…')` calls. Same non-2xx rejection behavior, matches the declared pattern, and mirrors 03-01's existing `/venues` call style that Plan 03-03 will extend.
- **Files modified:** `iris/PopHeat/www/dashboard.html`
- **Verification:** `grep -E "fetch\(.*(counts|telemetry|status)"` → 3 matches; degraded-path probe re-run after the refactor, still `jsErrors=0`
- **Committed in:** `17f666a`

---

**Total deviations:** 5 auto-fixed (2 bugs, 2 Rule-2 additions, 1 blocking). **Impact:** No scope creep — all five are confined to the single file the plan declares. Both bugs were caught only because the page was rendered rather than inspected, and both would have been visible to a judge.

## Known Stubs

None. Every panel is wired to a live endpoint; there is no placeholder data path that survives a successful fetch.

## Threat Flags

None. This plan adds no network endpoint, auth path, file access or schema change. T-03-06 (CDN tampering) is now mitigated as planned: all three CDN tags carry `integrity` + `crossorigin`. The one security-relevant surface discovered — unescaped OSM-sourced strings in popup HTML — was closed in the same pass (deviation 4).

## Issues Encountered

- **`CRITICO` was 0 in every sample taken this session**, as it was for 03-01. The synthetic model simply does not reach the CRITICO threshold at this time of day. The CRITICO render path is therefore proven by a synthetic-data in-browser probe rather than by live data; if a judge should see a red marker on demo day, the heat-threshold configuration is what to adjust, not this page.
- **Throughput/elapsed numbers are browser-locale formatted** (`toLocaleString`), so a Portuguese browser shows `0,003s` and `43.249/s`. Intentional and appropriate for the contest audience, but worth knowing it is not a fixed format.
- **Headless-screenshot height is not the viewport height.** `--window-size=1400,900` yields an 813px viewport and pads the PNG to 900px, which initially looked like a layout gap below the map. Direct measurement confirmed `mapBottom == innerHeight == 813` — the map does fill its space. Noted so it is not re-investigated.

## User Setup Required

None. `docker compose up -d` followed by `docker compose exec -T iris sh /irisdev/app/docker/init-production.sh` yields the working dashboard at `http://localhost:52773/csp/popheat/dashboard.html`. `data/venues.json` (gitignored) must exist in the repo root for the pipeline to persist readings — regenerate with `python3 scripts/build_catalog.py --config config/catalog_build.json`.

## Next Phase Readiness

**Ready for Plan 03-03.** The seam is deliberate: `loadAll()` performs one full refresh cycle with four independent fetches, and every render function already clears its own prior output, so 03-03's work is to wrap `loadAll()` in `setInterval(..., 10000)` (D-08), attach the D-07 stale-data banner to individual fetch rejections, and add the "No readings yet" empty state. No restructuring is needed.

**Two constraints 03-03 must respect:**

1. **Keep `dashboard.html` pure ASCII.** The page is served as ISO-8859-1. 03-07's locked banner copy — "Unable to refresh — showing last known data as of {time}" — contains an **em dash** and will mojibake unless written as `&mdash;` or `String.fromCharCode(8212)`. Verify with `grep -P '[^\x00-\x7F]' iris/PopHeat/www/dashboard.html` returning nothing.
2. **Any element toggled with the `hidden` attribute that also has an author `display` rule needs a companion `[hidden]` selector.** The empty-state and banner elements 03-03 adds will hit this same trap.

---
*Phase: 03-dashboard-api*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: `iris/PopHeat/www/dashboard.html`
- FOUND: commit `e24baae` (Task 1), commit `17f666a` (Task 2)
- VERIFIED: Task 1 `<verify>` automated → `EXIT:0`
- VERIFIED: Task 2 `<verify>` automated → `EXIT:0`
- VERIFIED: plan `<verification>` 1–4 all pass against the live stack (heat layer + restricted markers rendered; `/counts` matched a direct SQL `ROW_NUMBER()` cross-check exactly; badge tracked a real stop/start of `PopHeat.Production` without hiding any data; 3/3 CDN tags carry `integrity` + `crossorigin`)
- VERIFIED: `grep -P '[^\x00-\x7F]'` on `dashboard.html` → no matches (pure ASCII)
- VERIFIED: no probe/temp files remain — `git status --short` clean apart from the intended changes
