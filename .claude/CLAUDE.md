<!-- GSD:project-start source:PROJECT.md -->

## Project

**PopHeat**

PopHeat is a live heat map showing how crowded bars, restaurants, cafés, and other nightlife/food venues currently are. It's built as an InterSystems IRIS Interoperability Production (PyProd) that ingests a venue catalog sourced from OpenStreetMap, computes a synthetic popularity score per venue, classifies each reading into a business-facing crowdedness label, and serves a live-updating dashboard. It's being built as a solo entry for the InterSystems Portugal 2026 Programming Contest.

**Core Value:** A working, submittable IRIS PyProd application, live and functioning end-to-end (ingest → score → classify → persist → dashboard), by the contest deadline. If the demo isn't running and the submission isn't in, nothing else about the project matters.

### Constraints

- **Timeline**: Working live demo required by 2026-09-21 — about one day from kickoff. Drives aggressive scope-cutting and vertical-slice execution over completeness.
- **Tech stack**: Backend must run on InterSystems IRIS. The ingestion pipeline should specifically be built as an IRIS Interoperability Production using embedded Python (PyProd) to qualify for the contest's PyProd track.
- **Compliance**: Popularity must never depend on a live scraped or ToS-violating "busy now" source — synthetic model only, per `specs/popularity-model.spec`.
- **Submission format**: The deliverable must package as an Open Exchange application (English-language) with an accompanying Portuguese-language article — this shapes README/documentation needs, not just code.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->

## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
