# Phase 1: Venue Catalog Sourcing - Pattern Map

**Mapped:** 2026-09-20
**Files analyzed:** 4 (inferred from CONTEXT.md decisions)
**Analogs found:** 0 / 4

## Greenfield Notice

This repository has **no existing code** outside `.git/`, `.planning/`, `.claude/`, and `specs/*.spec`. Verified via:

```
find /home/jean/git/popheat -type f -not -path '*/.git/*' -not -path '*/.planning/*' -not -path '*/.claude/*' -not -path '*/specs/*'
```

returned zero results. There are no controllers, services, scripts, or configs anywhere in the tracked tree to serve as analogs. **Planning should proceed without pattern-reuse constraints** — files in this phase will establish the first conventions for the project (import style, error handling, CLI structure, config format), not follow existing ones.

## File Classification

Files inferred from `01-CONTEXT.md` decisions (D-01 through D-13):

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|-----------------|----------------|
| `scripts/build_catalog.py` | utility (CLI entrypoint) | request-response (Overpass API call) + batch (transform/dedup/write) | none | no analog |
| `scripts/overpass_client.py` (or inline in build_catalog.py) | service (external API client) | request-response | none | no analog |
| `config/catalog_build.{json,yaml,toml}` (bounding box, amenity allowlist) | config | — | none | no analog |
| `data/venues.json` (generated artifact, gitignored) | — (build output, not source) | file-I/O | none | no analog |
| `data/venues.raw.json` (raw Overpass snapshot, gitignored, per D-06) | — (build output, not source) | file-I/O | none | no analog |
| `.gitignore` (add `data/venues.json`, raw snapshot per D-09) | config | — | none | no analog (file does not exist yet; create fresh) |

Note: exact filenames/module split are Claude's discretion per D-10/D-13 and should be finalized in the plan, not here.

## Pattern Assignments

No pattern assignments — no analog source exists to extract imports, auth, core-pattern, error-handling, or validation excerpts from. The planner should instead derive conventions directly from:

- `specs/venue-sourcing.spec` — authoritative business rules (R1 eligibility tags, R2 required fields, R3 bounding-box scope as config, R4 5-decimal dedup, R5 stable identity, R6 manual/on-demand regeneration).
- `specs/ingestion-pipeline.spec` — downstream consumer contract shaping field naming (D-08) and batch-read expectations (batches of 150).
- `01-CONTEXT.md` decisions D-01 through D-13 (bounding box, Overpass endpoint-only with no fallback, fail-loudly-and-preserve-last-good-catalog on error, JSON output, gitignored artifacts, standalone Python CLI, run-summary printing, overwrite-with-no-backup, config-file-driven build parameters).

Since this is genuinely the first code in the repo, the planner/executor should establish idiomatic, simple Python patterns directly (e.g., `requests` or `urllib` for the Overpass POST query, `argparse` or plain `sys.argv` for CLI invocation, `json` stdlib for read/write, a small dataclass or dict-based venue record) rather than reverse-engineering conventions that don't exist yet.

## Shared Patterns

None identified — no cross-cutting auth, error-handling, or response-formatting conventions exist in the codebase to reuse. The phase itself will define the first shared pattern: "fail loudly with non-zero exit and leave `data/venues.json` untouched on Overpass failure" (D-05), which subsequent phases (e.g., Phase 2 PyProd ingestion) may later reference back to this phase's script as their own first analog.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `scripts/build_catalog.py` | utility | request-response + batch | Greenfield repo — no scripts directory or CLI precedent exists |
| Overpass client logic | service | request-response | No external API client code exists anywhere in the repo |
| `config/catalog_build.*` | config | — | No config files/loading pattern exists anywhere in the repo |
| `data/venues.json`, raw snapshot | build artifact | file-I/O | Generated outputs, gitignored; no prior JSON-writing code exists |

## Metadata

**Analog search scope:** entire repository tree, excluding `.git/`, `.planning/`, `.claude/`, `specs/`
**Files scanned:** 0 source files found (repo contains only markdown/spec/planning files)
**Pattern extraction date:** 2026-09-20
**Recommendation:** Planner should treat this phase as pattern-setting rather than pattern-following. Keep the CLI script simple and idiomatic (stdlib-first: `json`, `urllib.request` or a single `requests` dependency, `argparse`), since there is no established dependency-management convention yet either (no `requirements.txt`/`pyproject.toml` present).
