---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-09-20T18:25:00.618Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 02 | unrun-verify | iris/PopHeat/BatchTelemetry.cls |  | Plan 02-02 verification item 3: BatchTelemetry.cls RecentBatches() compile via $SYSTEM.OBJ.LoadDir and live query not run -- Docker daemon inaccessible in execution sandbox | open |  | 2026-09-20T18:24:54.295Z |  |
| 2 | 02 | unrun-verify | popheat_pipeline/components.py |  | Plan 02-02 verification item 2: live multi-tick production run (two distinct 150-venue batches, broken-batch error isolation, BatchTelemetry accumulation) not run against real IRIS -- Docker daemon inaccessible in execution sandbox; verified instead via unit tests + live-stubbed iop instantiation trial | open |  | 2026-09-20T18:25:00.618Z |  |

````json
[
  {
    "id": 1,
    "kind": "unrun-verify",
    "phase": "02",
    "file": "iris/PopHeat/BatchTelemetry.cls",
    "line": null,
    "description": "Plan 02-02 verification item 3: BatchTelemetry.cls RecentBatches() compile via $SYSTEM.OBJ.LoadDir and live query not run -- Docker daemon inaccessible in execution sandbox",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T18:24:54.295Z",
    "resolved_at": null,
    "milestone": null
  },
  {
    "id": 2,
    "kind": "unrun-verify",
    "phase": "02",
    "file": "popheat_pipeline/components.py",
    "line": null,
    "description": "Plan 02-02 verification item 2: live multi-tick production run (two distinct 150-venue batches, broken-batch error isolation, BatchTelemetry accumulation) not run against real IRIS -- Docker daemon inaccessible in execution sandbox; verified instead via unit tests + live-stubbed iop instantiation trial",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-09-20T18:25:00.618Z",
    "resolved_at": null,
    "milestone": null
  }
]
````
