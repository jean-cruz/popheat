# Phase 3 — UI Review

**Audited:** 2026-09-21
**Baseline:** 03-UI-SPEC.md (status: approved)
**Screenshots:** not captured — no dev server reachable on 3000/5173/8080/52773 in this sandbox, and `docker` requires elevated permission not available here (`permission denied while trying to connect to the docker API`). This is a **code-only audit** of `iris/PopHeat/www/dashboard.html` and `iris/PopHeat/API.cls`, cross-referenced against the live headless-Chrome verification evidence already captured in 03-01/03-02/03-03-SUMMARY.md (DOM computed-style assertions, live SQL cross-checks, and five reviewed screenshots from the actual execution sessions).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every locked string (empty state, error banner, status badge, popup, counts, telemetry) matches 03-UI-SPEC.md verbatim; three additions are compliant extensions, not deviations |
| 2. Visuals | 4/4 | Clear hierarchy via Display/Heading/Label/Body sizing, dismiss control has `aria-label`, decorative dot is `aria-hidden` — no unlabeled icon-only controls |
| 3. Color | 3/4 | Accent (`#3B82F6`) correctly restricted to its 3 declared uses, but 3 hex values (`#FFFFFF`, `#9AA5B1`, `#616E7C`) are used in shipped CSS without appearing in the UI-SPEC Color table |
| 4. Typography | 3/4 | Introduces a 3rd font-weight (700, popup venue name) and an undeclared 13px/400 pairing (`.popup-note`) beyond the spec's 4 locked size/weight combinations |
| 5. Spacing | 4/4 | 100% of spacing values trace to the declared 4/8/16/24/32px scale or its two documented exceptions (240px popup width, 44px touch target) |
| 6. Experience Design | 3/4 | Strong state coverage (loading/error/empty/non-gating) with independent per-endpoint fetch isolation, but the phase's single most demo-critical behavior — the D-07 live banner appearing/clearing against a real container stop/restart — was never actually observed running; only `grep`-verified |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **The core "live" failure/recovery path (DASH-07) has never been watched running** — 03-03-SUMMARY.md states verbatim "No container was stopped or started during this execution run" and tracks the banner's real-world behavior as an outstanding `human_judgment: true` item. This is the exact behavior that makes the product "live" per the phase's own stated objective, and it is currently backed only by static `grep -q 'function recordFetchFailure'`-style checks, not an observed render. — **User impact:** if the banner's copy interpolation, dismiss handling, or auto-clear-on-recovery has any runtime bug (e.g. `lastSuccessfulFetchAt` formatting, a race between `dismissBanner()` and a fetch still in flight), it will surface for the first time in front of a judge. — **Fix:** before demo day, run `docker compose stop iris`, watch the banner appear with correct interpolated time, click dismiss, confirm it disappears, then `docker compose start iris` and confirm the banner auto-clears on the next successful 10s cycle — exactly as 03-03-PLAN.md's own `<human-check>` block specifies but which was never executed.

2. **Typography contract drift: an undeclared 700 weight and an undeclared 13px/400 pairing** — 03-UI-SPEC.md's Typography table declares exactly 4 role/size/weight combinations (Body 16/400, Label 13/600, Heading 20/600, Display 28/600), both because it says only two weights (400, 600) are in scope. `.popup-name { font-weight: 700; }` (dashboard.html:322) and `.popup-note { font-size: 13px; ... }` with no weight override, inheriting `font-weight: 400` from `body` (dashboard.html:325, 62) — introduce a 5th size/weight combination (16px/700) and an undocumented 13px/400 combination that don't map to any declared role. — **User impact:** none visually (the bold venue name and muted note read fine), but the design contract can no longer be mechanically audited against what's shipped — the next reviewer has no declared baseline to check these two rules against. — **Fix:** either amend 03-UI-SPEC.md's Typography table to add a "Popup Name (bold Body, 16px/700)" and "Popup Note (13px/400)" row, or change `.popup-name` to `font-weight: 600` and `.popup-note` to explicitly set `font-weight: 600` to stay inside the two declared weights.

3. **Color contract drift: 3 hex values used but not declared** — 03-UI-SPEC.md's Color table declares exactly 8 hex values (Dominant, Secondary, Accent, Destructive, and the 4 heat colors). Shipped CSS additionally defines `--chrome-text: #FFFFFF` (dashboard.html:42), `--chrome-muted: #9AA5B1` (dashboard.html:43), and a one-off `.popup-note { color: #616E7C; }` (dashboard.html:325) that isn't even routed through a CSS custom property like the other two. — **User impact:** none directly (white-on-dark and two muted grays are reasonable, low-risk choices), but `#616E7C` in particular is a magic hex value with no named token, meaning a future palette change would silently miss it. — **Fix:** add a `--chrome-muted-2: #616E7C` (or reuse `--chrome-muted` for the popup note) and document both `#FFFFFF` and the muted gray(s) in 03-UI-SPEC.md's Color table as "chrome text / secondary text," matching how the other tokens are documented.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

Verified every locked string in `iris/PopHeat/www/dashboard.html` against 03-UI-SPEC.md's Copywriting Contract line by line:

- Empty state heading `"No readings yet"` (line 359) and body copy (line 360) — exact match, em dash correctly built via `&mdash;` entity to survive the page's ISO-8859-1 serving charset.
- Error banner copy assembled at runtime (`recordFetchFailure()`, lines 641–649): `'Unable to refresh ' + EM_DASH + ' showing last known data as of ' + asOf + '.'` — matches the D-07 locked string exactly, with `EM_DASH = String.fromCharCode(8212)` correctly avoiding the mojibake bug the team already hit once on `MIDDOT` (documented in 03-02-SUMMARY.md's first deviation).
- Status badge: `"Pipeline: Running"` / `"Pipeline: Stopped"` (lines 341, 578) — exact match, text label always rendered alongside the dot per the "color is never the sole signal" requirement.
- Marker popup structure (`buildPopupHtml`, lines 555–564) — venue name bold, `"{Category} · {HeatLevel}"` in the matching heat color, `"Popularity: {score}"`, `"as of {time}"` in accent color — all four lines present and ordered as specified.
- Counts panel (lines 369–374) and telemetry panel (`renderTelemetry`, lines 597–607) — both match the declared format strings.
- Banner dismiss control: `aria-label="Dismiss"` (line 351) — matches the checker's Dimension 2 flag requirement exactly.

Three copy additions beyond the locked contract (top-bar subtitle "Synthetic crowdedness estimates · not measured crowd counts," popup note "Estimated crowdedness, not a safety warning.," and the status badge's `title` attribute) are documented in 03-02-SUMMARY.md as intentional additions satisfying the plan's own DASH-02/DASH-04/DASH-06 prohibitions — none replaces or contradicts a locked string, so these are compliant extensions rather than deviations. No generic labels ("Submit," "Click Here," "OK," "Cancel," "Save") appear anywhere in the file (`grep` returned zero matches).

### Pillar 2: Visuals (4/4)

- Clear focal point: the map fills the entire viewport below the 56px top bar (`#map { position: absolute; top: var(--topbar-height); ... }`, line 184), with floating chrome panels layered above it — standard, unambiguous dashboard hierarchy.
- Icon-only interactive elements are correctly labeled: `#stale-banner-dismiss` carries `aria-label="Dismiss"` (line 351); the decorative status dot carries `aria-hidden="true"` (line 340) since its meaning is fully conveyed by the adjacent text label — correct accessible pattern, not decoration masquerading as the only signal.
- Visual hierarchy is achieved through the declared type scale alone (Display 28/600 for counts, Heading 20/600 for the title, Label 13/600 for secondary chrome text, Body 16/400 for prose) plus color-coding per heat level — no ad hoc hierarchy hacks.
- Z-index layering is coherent: banner (1200) > top bar (1100) > empty-state/panels (1000), with no spatial overlap between the banner and the top bar in practice since the banner is positioned to start exactly at `--topbar-height`.
- Minor, out-of-scope-for-contract note: Leaflet's native zoom control, popup close button, and OSM attribution render in their unstyled library-default appearance rather than matching the app's dark/accent palette. 03-UI-SPEC.md's Design System section declares no rule for third-party map-primitive chrome, so this isn't a contract violation — noted for completeness, not scored against.

### Pillar 3: Color (3/4)

Accent-blue (`#3B82F6`) usage was grepped and confirmed restricted to exactly its 3 declared roles: the running status dot (line 124), the dismiss button's hover/focus state (line 180), and the popup timestamp (line 324) — no accent bleed into any other interactive element, which is the exact 60/30/10-adjacent discipline the spec calls for ("never for all interactive elements").

However, 3 hex values ship in the CSS that do not appear anywhere in 03-UI-SPEC.md's Color table (which declares exactly 8: `#F5F6F8`, `#1F2933`, `#3B82F6`, `#DC2626`, `#2ECC71`, `#F1C40F`, `#E67E22`, `#E74C3C`):

- `--chrome-text: #FFFFFF` (line 42) — white text on dark chrome, functionally necessary but never named as a token in the contract.
- `--chrome-muted: #9AA5B1` (line 43) — used for the subtitle, stopped-state label, panel titles, and placeholder text (5 call sites).
- `.popup-note { color: #616E7C; }` (line 325) — a fourth, entirely separate gray, not even routed through the `--chrome-muted` custom property the rest of the file uses consistently.

None of these represent accent misuse or heat-gradient confusion — the actual risk (accent bleeding into chrome, or heat colors reused for chrome) that the spec is designed to prevent is fully avoided. This is a documentation/token-discipline gap, not a color-scheme integrity problem, which is why it lands at 3/4 rather than lower.

### Pillar 4: Typography (3/4)

Font sizes in use: `13px, 16px, 20px, 28px` — exactly the 4 sizes declared (Label/Body/Heading/Display). Font weights in use: `400, 600, 700` — the spec's Typography table declares only `400` and `600` across all four roles, so `700` is a 3rd, undeclared weight.

- `.popup-name { font-weight: 700; }` (line 322) — paired with the inherited 16px from `.leaflet-popup-content` (line 320), this produces a 16px/700 combination that matches none of the table's 4 rows (Body is defined as 16px/**400**). The Copywriting Contract's own text calls for the venue name to render "bold," which the Typography table doesn't formally accommodate — an inconsistency between the two spec sections, but the shipped code resolves it silently rather than surfacing the gap.
- `.popup-note { font-size: 13px; ... }` (line 325) has no explicit `font-weight`, so it inherits `400` from `body` (line 62) — producing a 13px/400 pairing, whereas the only declared 13px role (Label) is specified as 13px/**600**.

Visually this reads fine (bold names are conventional; a muted 400-weight caption below a 600-weight label is a reasonable secondary-text pattern), but it means the Typography contract as written no longer fully describes what's on screen — a mechanical audit against 03-UI-SPEC.md's literal table would fail these two rules.

### Pillar 5: Spacing (4/4)

Every spacing declaration in the file resolves to a CSS custom property from the declared scale — `--space-xs` (4px), `--space-sm` (8px), `--space-md` (16px), `--space-lg` (24px), `--space-xl` (32px) — with zero raw arbitrary spacing values found outside the scale. The two documented exceptions are both present and correctly scoped: `.popup-content { max-width: 240px; }` (line 321, marker-radii/popup-width exception) and `#stale-banner-dismiss { min-width: 44px; min-height: 44px; }` (lines 165–166, touch-target exception). Layout dimensions match exactly: top bar `56px` (lines 49, 67), map filling the remainder via `top: var(--topbar-height)`. Border-radius (`8px`) and border-width (`1px`/`2px`) values are decorative/structural, not spacing-scale items, and are conventionally exempt from this check.

### Pillar 6: Experience Design (3/4)

State coverage is genuinely strong and code-verified:

- **Loading:** counts and telemetry panels show a "Loading live data…" placeholder until first successful fetch (lines 368, 380, `renderCounts`/`renderTelemetry` guard logic), with a documented and fixed CSS-specificity bug (`#counts-rows[hidden]`) that would otherwise have leaked fabricated zeros through the placeholder — caught and fixed per 03-02-SUMMARY.md deviation 2.
- **Error:** `recordFetchFailure()` (lines 641–649) touches only the banner's own DOM nodes, never the venue/counts/telemetry/status regions — structurally enforcing the "stale data stays visible" requirement rather than relying on convention.
- **Empty:** `renderVenues()` (lines 624–634) shows the "No readings yet" box only on a successfully-parsed empty array, explicitly distinct from the failure path — correct per the spec's own emphasis that empty and error must never be conflated.
- **Non-gating status:** `renderStatus()` (lines 572–579) touches only the badge DOM; `Status()` in `API.cls` (lines 115–132) never propagates an exception to the client.
- **Concurrency safety:** `isRefreshing` in-flight guard plus independent `fetchRegion()` calls per endpoint with their own `AbortController` timeout (8s, shorter than the 10s interval) — a well-reasoned design against overlapping cycles and wedged connections.

The gap: DASH-07 is this phase's headline requirement ("this is the requirement that makes the dashboard 'live' rather than a static snapshot," per 03-03-PLAN.md's own objective), and its most consequential runtime behavior — banner appearing on a genuine connection loss, staying accurate, dismissing, and auto-clearing on real recovery — has been verified only by `grep` pattern-matching against the source text (per 03-03-SUMMARY.md's coverage table, `verification: kind: other, ref: grep -q ...`), not by an actual observed run. 03-03-SUMMARY.md states this explicitly: "No container was stopped or started during this execution run," and flags it as an outstanding UAT item. This sandbox could not close that gap either (no dev server, no docker permission), so it remains unverified as of this audit. Everything else in this pillar is solid, which is why this lands at 3/4 (notable gap in the single riskiest path) rather than lower.

---

## Registry Safety

Not applicable — `components.json` does not exist in this repository, and 03-UI-SPEC.md's own Registry Safety section confirms "no shadcn, no component registry of any kind is used in this phase." Skipped per the audit protocol.

---

## Files Audited

- `iris/PopHeat/www/dashboard.html` (full file, 744 lines — HTML, CSS, and vanilla JS)
- `iris/PopHeat/API.cls` (full file, 135 lines — `%CSP.REST` dispatch class)
- `.planning/phases/03-dashboard-api/03-UI-SPEC.md` (design contract baseline)
- `.planning/phases/03-dashboard-api/03-CONTEXT.md` (locked decisions D-01 through D-08)
- `.planning/phases/03-dashboard-api/03-01-PLAN.md` / `03-01-SUMMARY.md`
- `.planning/phases/03-dashboard-api/03-02-PLAN.md` / `03-02-SUMMARY.md`
- `.planning/phases/03-dashboard-api/03-03-PLAN.md` / `03-03-SUMMARY.md`
