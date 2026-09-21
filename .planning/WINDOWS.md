---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 3
total_count: 4
last_updated: 2026-09-21T11:26:12.688Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | unrun-verify | iris/PopHeat/BatchTelemetry.cls |  | Plan 02-02 verification item 3: BatchTelemetry.cls RecentBatches() compile via $SYSTEM.OBJ.LoadDir and live query not run -- Docker daemon inaccessible in execution sandbox | fixed |  | 2026-09-20T18:24:54.295Z | 2026-09-20T21:23:50.564Z |
| 2 | 02 | unrun-verify | popheat_pipeline/components.py |  | Plan 02-02 verification item 2: live multi-tick production run (two distinct 150-venue batches, broken-batch error isolation, BatchTelemetry accumulation) not run against real IRIS -- Docker daemon inaccessible in execution sandbox; verified instead via unit tests + live-stubbed iop instantiation trial | fixed |  | 2026-09-20T18:25:00.618Z | 2026-09-20T21:23:50.664Z |
| 3 | 03 | unrun-verify | iris/PopHeat/API.cls |  | GET /venues returns HTTP 403 live (and /dashboard.csp 404) despite AutheEnabled=64 + UnknownUser role/resource grant + %Service_WebGateway fix; tracer <verify> could not be made to pass, root cause undiagnosed -- see 03-01-SUMMARY.md Known Issues | fixed |  | 2026-09-21T09:40:30.605Z | 2026-09-21T10:46:23.068Z |
| 4 | 03 | deviation | iris/PopHeat/www/dashboard.html |  | IRIS serves /csp/popheat static files as charset=ISO-8859-1, which overrides <meta charset=UTF-8>; dashboard.html is kept pure ASCII to compensate. Plan 03-03's banner copy uses an em dash and MUST use an entity/char-code, or fix the web application's charset. | open |  | 2026-09-21T11:26:12.688Z |  |

````json
[
  {
    "id": 1,
    "kind": "unrun-verify",
    "phase": "02",
    "file": "iris/PopHeat/BatchTelemetry.cls",
    "line": null,
    "description": "Plan 02-02 verification item 3: BatchTelemetry.cls RecentBatches() compile via $SYSTEM.OBJ.LoadDir and live query not run -- Docker daemon inaccessible in execution sandbox",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-20T18:24:54.295Z",
    "resolved_at": "2026-09-20T21:23:50.564Z",
    "milestone": null
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "02",
    "file": "popheat_pipeline/components.py",
    "line": null,
    "description": "Plan 02-02 verification item 2: live multi-tick production run (two distinct 150-venue batches, broken-batch error isolation, BatchTelemetry accumulation) not run against real IRIS -- Docker daemon inaccessible in execution sandbox; verified instead via unit tests + live-stubbed iop instantiation trial",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-20T18:25:00.618Z",
    "resolved_at": "2026-09-20T21:23:50.664Z",
    "milestone": null
  },
  {
    "id": 3,
    "kind": "unrun-verify",
    "phase": "03",
    "file": "iris/PopHeat/API.cls",
    "line": null,
    "description": "GET /venues returns HTTP 403 live (and /dashboard.csp 404) despite AutheEnabled=64 + UnknownUser role/resource grant + %Service_WebGateway fix; tracer <verify> could not be made to pass, root cause undiagnosed -- see 03-01-SUMMARY.md Known Issues",
    "status": "fixed",
    "reason": "",
    "recorded_at": "2026-09-21T09:40:30.605Z",
    "resolved_at": "2026-09-21T10:46:23.068Z",
    "milestone": null
  },
  {
    "id": 4,
    "kind": "deviation",
    "phase": "03",
    "file": "iris/PopHeat/www/dashboard.html",
    "line": null,
    "description": "IRIS serves /csp/popheat static files as charset=ISO-8859-1, which overrides <meta charset=UTF-8>; dashboard.html is kept pure ASCII to compensate. Plan 03-03's banner copy uses an em dash and MUST use an entity/char-code, or fix the web application's charset.",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-21T11:26:12.688Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
