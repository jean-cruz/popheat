"""PopHeat IoP production: poll -> score/classify -> persist (INGE-01).

Real, spec-complete pipeline (Plan 02-02): CatalogPollingService cycles the
full venue catalog in 150-venue, 3-second-cadence batches via circular
(modulo) indexing (INGE-02, INGE-03), ScoreClassifyProcess computes the
REAL, final popularity + heat-classification math for every venue in the
batch using thresholds re-read fresh from config every call (HEAT-03/D-10),
and PersistOperation inserts every reading in the batch plus one
PopHeat.BatchTelemetry row via the embedded-Python object-persistence API.

The pure popularity/classification/batching math lives in
`popheat_pipeline/scoring.py` (IRIS-independent, unit-tested) -- this module
imports from it rather than duplicating the logic.

See specs/popularity-model.spec, specs/heat-classification.spec,
specs/telemetry.spec, specs/ingestion-pipeline.spec, and
.planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/
02-CONTEXT.md (D-01, D-02, D-06, D-07, D-09, D-10) for the business rules
implemented here.
"""

import json
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from iop import BusinessOperation, BusinessProcess, Message, PollingBusinessService, target

from popheat_pipeline.scoring import (
    classify_heat,
    compute_popularity,
    load_thresholds,
    select_batch,
)

# D-02: "current time" for peak-hour distance and the weekend boost is
# Europe/Lisbon local time, not UTC -- venues are physically in Porto.
LISBON_TZ = ZoneInfo("Europe/Lisbon")

# Resolved relative to this file's location, NOT a hardcoded container path,
# so it works regardless of IRIS's process cwd (repo_root/popheat_pipeline/
# components.py -> repo_root/data/venues.json).
VENUES_PATH = Path(__file__).resolve().parent.parent / "data" / "venues.json"

# HEAT-03/D-10: heat thresholds live in a config file, re-read fresh at the
# start of every batch cycle (never cached) -- editing the file changes
# behavior on the next 3-second tick with no restart.
HEAT_THRESHOLDS_PATH = Path(__file__).resolve().parent.parent / "config" / "heat_thresholds.json"

# INGE-02: exactly 150 venues per batch.
BATCH_SIZE = 150


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@dataclass
class CatalogBatch(Message):
    """One or more venues acquired from data/venues.json for this poll."""

    venues: list
    batch_started_at: str


@dataclass
class ScoredBatch(Message):
    """Venues from a CatalogBatch after scoring + classification."""

    readings: list
    batch_started_at: str


# ---------------------------------------------------------------------------
# Production components (INGE-01: service -> process -> operation)
# ---------------------------------------------------------------------------


class CatalogPollingService(PollingBusinessService):
    """Acquires venues from the static catalog (INGE-01, R5).

    Walks the full catalog in fixed-size (150-venue) batches via circular
    (modulo) indexing (INGE-02, INGE-03): `_cursor` is in-memory state that
    advances every poll and wraps back to 0 once it passes the end of the
    catalog, so every venue is revisited on a regular cycle rather than
    just once. The WHOLE batch travels as one `CatalogBatch` message, never
    split into per-venue messages (INGE-04). An empty catalog is a no-op
    tick (logged, not a crash) rather than a modulo-by-zero/divide-by-zero.

    `Output` carries an explicit default target name (rather than a bare
    `target()`) because the polling-triggered call path invokes `on_poll()`
    with no underlying IRIS message context, and the live host setting for
    `Output` is not hydrated into the Python instance before that call --
    `self.Output` reads back as `""` on every poll without a class-level
    default to fall back to (verified live: this project's own
    `settings.py.connect(...)` call still governs the real production graph
    edge; the default here only backstops the same value for polling-path
    reads).
    """

    Output = target("ScoreClassifyProcess")

    def on_init(self):
        # `iop` never calls `__init__` on business hosts -- cursor state
        # must be initialized here, not in `__init__` (INGE-02/INGE-03).
        self._cursor = 0

    def on_poll(self):
        with open(VENUES_PATH, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        if not catalog:
            self.log_info(f"Catalog at {VENUES_PATH} is empty; skipping poll")
            return

        batch, self._cursor = select_batch(catalog, self._cursor, BATCH_SIZE)
        if not batch:
            self.log_info(f"Catalog at {VENUES_PATH} is empty; skipping poll")
            return

        batch_started_at = datetime.now(LISBON_TZ).isoformat()
        self.send_request_async(
            self.Output,
            CatalogBatch(venues=batch, batch_started_at=batch_started_at),
        )


class ScoreClassifyProcess(BusinessProcess):
    """Computes popularity + heat level for every venue in a CatalogBatch.

    Owns validation/transform only -- no destination I/O here (that is
    PersistOperation's job). Recomputes popularity fresh for every venue on
    every call (POPU-06/R6); never reads PopHeat.Reading. Loads heat
    thresholds fresh from config/heat_thresholds.json at the START of every
    call -- never cached across calls or stored on `self` (HEAT-03/D-10) --
    so an operator edit to the config file takes effect on the very next
    batch with no restart.
    """

    Persist = target("PersistOperation")

    def on_message(self, request: CatalogBatch):
        thresholds = load_thresholds(str(HEAT_THRESHOLDS_PATH))
        when = datetime.now(LISBON_TZ)
        observed_at = when.isoformat()

        readings = []
        for venue in request.venues:
            category = venue.get("category")
            popularity = compute_popularity(category, when)
            heat_level = classify_heat(category, popularity, thresholds)
            readings.append(
                {
                    "venue_id": venue.get("id"),
                    "name": venue.get("name"),
                    "category": category,
                    "lat": venue.get("lat"),
                    "lon": venue.get("lon"),
                    "popularity": popularity,
                    "heat_level": heat_level,
                    "observed_at": observed_at,
                }
            )

        return self.send_request_sync(
            self.Persist,
            ScoredBatch(readings=readings, batch_started_at=request.batch_started_at),
        )


def _to_iris_timestamp(iso_string: str) -> str:
    """Convert an ISO-8601 (tz-aware) string to an IRIS %TimeStamp logical
    value ("YYYY-MM-DD HH:MM:SS.FFF", no 'T' separator, no UTC offset --
    %TimeStamp has no timezone concept, so the Europe/Lisbon-local wall-clock
    value (D-02) is stored as-is)."""
    dt = datetime.fromisoformat(iso_string)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class PersistenceError(Exception):
    """Raised when saving a PopHeat.Reading or PopHeat.BatchTelemetry object
    fails (a non-OK %Status from ._Save())."""


class PersistOperation(BusinessOperation):
    """Persists a ScoredBatch as PopHeat.Reading rows plus exactly one
    PopHeat.BatchTelemetry row (TELE-01, TELE-02).

    Uses the embedded-Python object-persistence API (`iris.cls(...)._New()`
    / `._Save()`) rather than `iris.sql.exec(...)`: every venue-derived value
    is assigned directly to a typed object property, so there is no SQL
    string to build at all -- not even a parameterized one -- closing off
    SQL injection (T-02-01) more completely than parameter binding would.
    (Deviation from the plan's literal `iris.sql.exec` instruction: this
    exact image's embedded-SQL query compiler throws
    `SQLError: <UNIMPLEMENTED>term+110^%qaqpslx` for ANY `iris.sql.exec`
    parameterized INSERT executed from inside a running Business
    Operation's own worker process -- reproduced consistently, including
    via `iris.sql.prepare` in `on_init()` -- while the identical statement
    succeeds from a standalone `irispython` script outside any production
    job. Rule 3 blocking-issue fix: the object API sidesteps the SQL
    compiler entirely and is unaffected.) PopHeat.Reading is insert-only
    (INGE-07, D-07); this file never modifies or removes an existing row.
    """

    def on_message(self, request: ScoredBatch):
        import iris

        start = time.monotonic()
        for reading in request.readings:
            obj = iris.cls("PopHeat.Reading")._New()
            obj.VenueId = reading["venue_id"]
            obj.VenueName = reading["name"]
            obj.Category = reading["category"]
            obj.Latitude = reading["lat"]
            obj.Longitude = reading["lon"]
            obj.Popularity = reading["popularity"]
            obj.HeatLevel = reading["heat_level"]
            obj.ObservedAt = _to_iris_timestamp(reading["observed_at"])
            status = obj._Save()
            if not status:
                raise PersistenceError(f"Failed to save PopHeat.Reading: {status}")
        elapsed = time.monotonic() - start

        count = len(request.readings)
        # TELE-03: zero-safety -- throughput is 0, never divided-by-zero,
        # when elapsed time is zero or unavailable.
        throughput = count / elapsed if elapsed > 0 else 0

        telemetry = iris.cls("PopHeat.BatchTelemetry")._New()
        telemetry.ReadingCount = count
        telemetry.ElapsedSeconds = round(elapsed, 3)
        telemetry.Throughput = round(throughput, 3)
        telemetry.RecordedAt = _to_iris_timestamp(datetime.now(LISBON_TZ).isoformat())
        status = telemetry._Save()
        if not status:
            raise PersistenceError(f"Failed to save PopHeat.BatchTelemetry: {status}")

        return request
