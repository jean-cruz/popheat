"""
PopHeat - Pure-Python IRIS Interoperability Production (PyProd)

Pipeline: OverpassInAdapter -> VenueIngestService -> HeatClassifierProcess -> HeatPersistOperation

Real venue locations (name/category/lat/lon) come from a dataset extracted from
OpenStreetMap (Overpass API) for Porto, Portugal - see data/fetch_venues.py.
Google/Foursquare do not offer a free, ToS-safe live "how busy is this place"
API (see project README), so the crowdedness score itself is a transparent
synthetic model driven by category + time of day + day of week, computed fresh
on every cycle. The heat-level classification (BAIXO/MEDIO/ALTO/CRITICO) is
delegated to a real InterSystems IRIS Business Rule (PopHeat.Rule.HeatLevel),
not hardcoded in Python, so a business analyst can tune thresholds per venue
category from the Rule Editor without touching code.
"""
import json
import math
import random
import time
from datetime import datetime
from pathlib import Path

from intersystems_pyprod import (
    InboundAdapter,
    BusinessService,
    BusinessProcess,
    BusinessOperation,
    Column,
    JsonSerialize,
    PickleSerialize,
    IRISProperty,
    IRISParameter,
    IRISLog,
    Status,
    Production,
    ServiceItem,
    ProcessItem,
    OperationItem,
)

iris_package_name = "PopHeat"

VENUES_FILE = Path("/opt/popheat/data/porto_venues.json")

# (peak_hour, width_hours, height) bumps per category, summed with circular
# hour distance so a peak near midnight wraps correctly (23h and 1h are close).
CATEGORY_CURVES = {
    "cafe": [(9, 2.0, 0.55), (15, 2.5, 0.25)],
    "restaurant": [(13, 1.5, 0.5), (20, 2.0, 0.75)],
    "fast_food": [(13, 1.5, 0.4), (20, 2.0, 0.5)],
    "bar": [(22, 2.0, 0.55), (1, 2.0, 0.7)],
    "pub": [(21, 2.0, 0.5), (0, 2.0, 0.6)],
    "nightclub": [(1, 2.0, 0.65), (3, 1.5, 0.55)],
}


def _circular_hour_distance(h1, h2):
    d = abs(h1 - h2)
    return min(d, 24 - d)


def synthetic_popularity(category, when):
    """Transparent, documented synthetic crowdedness model in [0, 1]."""
    hour = when.hour + when.minute / 60
    score = 0.05
    for peak, width, height in CATEGORY_CURVES.get(category, [(13, 3, 0.4), (20, 3, 0.4)]):
        d = _circular_hour_distance(hour, peak)
        score += height * math.exp(-(d ** 2) / (2 * width ** 2))
    if when.weekday() >= 4:  # Fri/Sat/Sun boost
        score *= 1.2
    score += random.uniform(-0.06, 0.06)
    return round(max(0.02, min(0.98, score)), 3)


class VenueReading(JsonSerialize):
    """SQL-queryable persisted table (one row per observation). Instances are
    created directly against IRIS (bypassing production messaging) from
    HeatPersistOperation for speed - see VenueBatch below for why."""
    venue_id: str = Column(index=True)
    name: str = Column()
    category: str = Column(index=True)
    lat = Column(datatype=float)
    lon = Column(datatype=float)
    popularity = Column(datatype=float)
    heat_level: str = Column(index=True)
    observed_at: str = Column()


class BatchMetric(JsonSerialize):
    """Telemetry: one row per processed batch, exposed on the dashboard's
    /api/telemetry endpoint (throughput, latency, batch size over time)."""
    batch_size = Column(datatype=int)
    elapsed_seconds = Column(datatype=float)
    venues_per_second = Column(datatype=float)
    recorded_at: str = Column(index=True)


class VenueBatch(PickleSerialize):
    """The actual message that travels Service -> Process -> Operation.

    Routing a whole batch (instead of one production message per venue) avoids
    ~2 synchronous inter-host round trips per venue: with ~1500 venues that is
    the difference between a full refresh in a few seconds versus tens of
    minutes, since each SendRequestSync hop carries tracing/queueing overhead.
    """
    readings: list = None


class OverpassInAdapter(InboundAdapter):
    """Cycles through the real OSM venue dataset, computing a fresh synthetic
    popularity reading for a batch of venues on every tick."""

    BATCH_SIZE: int = IRISParameter(value=150, description="Venues processed per tick")
    CALL_INTERVAL: int = IRISParameter(value=3, description="Seconds between ticks")

    def __init__(self, iris_host_object):
        super().__init__(iris_host_object)
        self.venues = json.loads(VENUES_FILE.read_text(encoding="utf-8"))
        self.cursor = 0

    def OnTask(self):
        status = Status.OK()
        try:
            time.sleep(self.CALL_INTERVAL)
            now = datetime.now()
            batch = self.venues[self.cursor: self.cursor + self.BATCH_SIZE]
            if not batch:
                self.cursor = 0
                batch = self.venues[0: self.BATCH_SIZE]
            else:
                self.cursor += self.BATCH_SIZE
            readings = []
            for venue in batch:
                reading = dict(venue)
                reading["popularity"] = synthetic_popularity(venue["category"], now)
                reading["observed_at"] = now.isoformat(timespec="seconds")
                readings.append(reading)
            status = self.business_host_process_input(readings)
        except Exception as e:
            IRISLog.Error("OverpassInAdapter.OnTask: " + str(e))
            status = Status.ERROR(str(e))
        return status


class VenueIngestService(BusinessService):
    ADAPTER: str = IRISParameter(value="PopHeat.OverpassInAdapter", description="Inbound adapter class")
    target_config_name = IRISProperty(
        settings="Target:selector?context={Ens.ContextSearch/ProductionItems?targets=1&productionName=@productionId}"
    )

    def OnProcessInput(self, input):
        status = Status.OK()
        try:
            batch = VenueBatch(readings=input)
            status = self.SendRequestSync(self.target_config_name, batch)
        except Exception as e:
            IRISLog.Error("VenueIngestService.OnProcessInput: " + str(e))
            status = Status.ERROR(str(e))
        return status


class HeatClassifierProcess(BusinessProcess):
    """Classifies crowdedness via the PopHeat.Rule.HeatLevel IRIS Business Rule
    (category-aware thresholds), instead of hardcoding if/elif in Python."""

    target_config_name = IRISProperty(
        settings="Target:selector?context={Ens.ContextSearch/ProductionItems?targets=1&productionName=@productionId}"
    )

    def OnRequest(self, request):
        status = Status.OK()
        try:
            import iris

            rule_def = iris.cls("Ens.Rule.Definition")
            ctx = iris.cls("PopHeat.Rule.Context")._New()
            classified = []
            for reading in request.readings:
                ctx.Popularity = reading["popularity"]
                ctx.Category = reading["category"]
                retval = iris.ref("")
                reason = iris.ref("")
                rule_def.EvaluateRules("PopHeat.Rule.HeatLevel", "", ctx, "", retval, reason)
                reading["heat_level"] = retval.value or "BAIXO"
                classified.append(reading)
            batch = VenueBatch(readings=classified)
            status, response = self.SendRequestSync(self.target_config_name, batch)
        except Exception as e:
            IRISLog.Error("HeatClassifierProcess.OnRequest: " + str(e))
            status, response = Status.ERROR(str(e)), None
        return status, response


class HeatPersistOperation(BusinessOperation):
    """Persists each reading directly as a PopHeat.VenueReading row, bypassing
    the production messaging layer per-row (see VenueBatch docstring)."""

    MessageMap = {"PopHeat.VenueBatch": "persist_batch"}

    def persist_batch(self, request):
        status = Status.OK()
        try:
            import iris

            started = time.perf_counter()
            saved = 0
            for reading in request.readings:
                rec = iris.cls("PopHeat.VenueReading")._New()
                rec.VenueId = reading["venue_id"]
                rec.name = reading["name"]
                rec.category = reading["category"]
                rec.lat = reading["lat"]
                rec.lon = reading["lon"]
                rec.popularity = reading["popularity"]
                rec.HeatLevel = reading["heat_level"]
                rec.ObservedAt = reading["observed_at"]
                rec._Save()
                saved += 1
            elapsed = time.perf_counter() - started

            metric = iris.cls("PopHeat.BatchMetric")._New()
            metric.BatchSize = saved
            metric.ElapsedSeconds = round(elapsed, 4)
            metric.VenuesPerSecond = round(saved / elapsed, 2) if elapsed > 0 else 0
            metric.RecordedAt = datetime.now().isoformat(timespec="seconds")
            metric._Save()

            IRISLog.Info(f"HeatPersistOperation: persisted {saved} readings in {elapsed:.2f}s")
            response = request
        except Exception as e:
            IRISLog.Error("HeatPersistOperation.persist_batch: " + str(e))
            status, response = Status.ERROR(str(e)), None
        return status, response


class PopHeatProduction(Production):
    description = "PopHeat: heatmap de lotacao de locais via PyProd"
    actor_pool_size = 4

    services = [
        ServiceItem(
            "PopHeat.VenueIngestService",
            "PopHeat.VenueIngestService",
            host_settings={"TargetConfigName": "PopHeat.HeatClassifierProcess"},
        )
    ]
    processes = [
        ProcessItem(
            "PopHeat.HeatClassifierProcess",
            "PopHeat.HeatClassifierProcess",
            host_settings={"TargetConfigName": "PopHeat.HeatPersistOperation"},
        )
    ]
    operations = [
        OperationItem(
            "PopHeat.HeatPersistOperation",
            "PopHeat.HeatPersistOperation",
        )
    ]
