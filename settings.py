"""iop --migrate entrypoint for PopHeat.Production (INGE-01).

Wires the tracer graph: CatalogPollingService -> ScoreClassifyProcess ->
PersistOperation. Batching (150/3s, R1) and full-catalog cycling (R2) are
added on top of this same graph in Plan 02-02.
"""

from iop import Production

from popheat_pipeline.components import (
    CatalogPollingService,
    PersistOperation,
    ScoreClassifyProcess,
)

prod = Production("PopHeat.Production", testing_enabled=True)

# CallInterval=3 previews ingestion-pipeline.spec R1's 3-second batch cadence
# (full batching lands in Plan 02-02) and keeps this tracer's poll well
# within any short post-start verification window.
service = prod.service(
    "CatalogPollingService",
    CatalogPollingService,
    adapter_settings={"CallInterval": 3},
)
process = prod.process("ScoreClassifyProcess", ScoreClassifyProcess)
operation = prod.operation("PersistOperation", PersistOperation)

service.connect(CatalogPollingService.Output, process)
process.connect(ScoreClassifyProcess.Persist, operation)

PRODUCTIONS = [prod]
