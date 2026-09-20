"""PopHeat IoP production: poll -> score/classify -> persist (INGE-01).

This is the phase's tracer slice: CatalogPollingService reads exactly one
venue from data/venues.json per poll (no batching/cycling -- that is Plan
02-02's INGE-01/R1/R2 job), ScoreClassifyProcess computes the REAL, final
popularity + heat-classification math (not a placeholder), and
PersistOperation inserts one PopHeat.Reading row plus one
PopHeat.BatchTelemetry row per poll via parameterized SQL.

See specs/popularity-model.spec, specs/heat-classification.spec,
specs/telemetry.spec, specs/ingestion-pipeline.spec, and
.planning/phases/02-iris-ingestion-pipeline-scoring-classification-telemetry/
02-CONTEXT.md (D-01, D-02, D-06, D-07) for the business rules implemented
here.
"""

import json
import math
import random
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from iop import BusinessOperation, BusinessProcess, Message, PollingBusinessService, target

# D-02: "current time" for peak-hour distance and the weekend boost is
# Europe/Lisbon local time, not UTC -- venues are physically in Porto.
LISBON_TZ = ZoneInfo("Europe/Lisbon")

# Resolved relative to this file's location, NOT a hardcoded container path,
# so it works regardless of IRIS's process cwd (repo_root/popheat_pipeline/
# components.py -> repo_root/data/venues.json).
VENUES_PATH = Path(__file__).resolve().parent.parent / "data" / "venues.json"


# ---------------------------------------------------------------------------
# Popularity model (specs/popularity-model.spec R1-R6)
# ---------------------------------------------------------------------------

# Each category maps to a list of (peak_hour, height, sigma_hours) tuples
# (POPU-02). sigma_hours = 1.7 for every peak, per D-01's "~2-hour
# half-width" guideline: a Gaussian's half-width-at-half-maximum equals
# sigma * sqrt(2 * ln(2)) ~= 1.1774 * sigma, so sigma=1.7 gives a half-width
# of ~2.00 hours. Heights are Claude's-discretion tuning (D-01/CONTEXT.md
# "Claude's Discretion"): fast_food's peaks are deliberately lower than
# restaurant's identical 13h/20h peaks, per the spec's explicit "lower
# intensity than restaurant" instruction.
_SIGMA = 1.7

CATEGORY_CURVES = {
    "cafe": [(9.0, 0.50, _SIGMA), (15.0, 0.50, _SIGMA)],
    "restaurant": [(13.0, 0.65, _SIGMA), (20.0, 0.65, _SIGMA)],
    "fast_food": [(13.0, 0.45, _SIGMA), (20.0, 0.45, _SIGMA)],
    "bar": [(22.0, 0.50, _SIGMA), (1.0, 0.50, _SIGMA)],
    "pub": [(21.0, 0.45, _SIGMA), (0.0, 0.45, _SIGMA)],
    "nightclub": [(1.0, 0.55, _SIGMA), (3.0, 0.55, _SIGMA)],
    "_default": [(13.0, 0.45, _SIGMA), (20.0, 0.45, _SIGMA)],
}

# Every score starts from this floor so popularity is never fully empty
# (POPU-01).
_BASE_FLOOR = 0.05
_MIN_POPULARITY = 0.02
_MAX_POPULARITY = 0.98
_WEEKEND_BOOST = 1.20
_RANDOM_ADJUSTMENT_RANGE = (-0.06, 0.06)
# Friday=4, Saturday=5, Sunday=6 (datetime.weekday()) -- POPU-04.
_WEEKEND_WEEKDAYS = (4, 5, 6)


def circular_distance(h1: float, h2: float) -> float:
    """Hour distance on a 24h circular clock (POPU-03): 23h to 1h is 2, not 22."""
    d = abs(h1 - h2) % 24
    return min(d, 24 - d)


def compute_popularity(category: str, when: datetime) -> float:
    """Compute a venue's synthetic popularity score at `when` (Lisbon-local).

    Fixed order (POPU-01 through POPU-05): category curve (MAX over peaks,
    never SUM, so nearby peaks like bar's 22h/1h don't stack) -> weekend
    boost -> random adjustment -> clamp to [0.02, 0.98] -> round to 3
    decimals. Never reads or caches a prior reading (POPU-06) -- recomputed
    fresh on every call from the given timestamp (POPU-06/R6).
    """
    hour = when.hour + when.minute / 60.0
    peaks = CATEGORY_CURVES.get(category, CATEGORY_CURVES["_default"])

    score = _BASE_FLOOR + max(
        height * math.exp(-(circular_distance(hour, peak_hour) ** 2) / (2 * sigma**2))
        for peak_hour, height, sigma in peaks
    )

    if when.weekday() in _WEEKEND_WEEKDAYS:
        score *= _WEEKEND_BOOST

    score += random.uniform(*_RANDOM_ADJUSTMENT_RANGE)

    score = max(_MIN_POPULARITY, min(_MAX_POPULARITY, score))
    return round(score, 3)


# ---------------------------------------------------------------------------
# Heat classification (specs/heat-classification.spec R1-R5)
# ---------------------------------------------------------------------------

NIGHTLIFE_CATEGORIES = {"bar", "pub", "nightclub"}

# Ordered highest-threshold-first (R3): first matching rule wins.
_NIGHTLIFE_SCALE = (("CRITICO", 0.60), ("ALTO", 0.40), ("MEDIO", 0.20))
_DAYTIME_SCALE = (("CRITICO", 0.75), ("ALTO", 0.50), ("MEDIO", 0.25))


def classify_heat(category: str, popularity: float) -> str:
    """Classify a popularity score into BAIXO/MEDIO/ALTO/CRITICO (R1-R5).

    Nightlife categories (bar/pub/nightclub) use a lower scale than daytime
    categories (R1/R2). Defaults to BAIXO -- including when classification
    itself fails for any reason (HEAT-04/R5) -- rather than leaving a
    reading unlabeled or raising.
    """
    try:
        scale = _NIGHTLIFE_SCALE if category in NIGHTLIFE_CATEGORIES else _DAYTIME_SCALE
        for label, threshold in scale:
            if popularity >= threshold:
                return label
        return "BAIXO"
    except Exception:
        return "BAIXO"


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

    Tracer scope: reads data/venues.json once per poll and takes only the
    FIRST venue -- no batching (150/3s, R1) or full-catalog cycling (R2) yet;
    that is Plan 02-02's job. This service owns the source read; it never
    emits an empty "fetch this" trigger.

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

    def on_poll(self):
        with open(VENUES_PATH, "r", encoding="utf-8") as f:
            venues = json.load(f)

        if not venues:
            self.log_warning(f"No venues found at {VENUES_PATH}; skipping poll")
            return

        venue = venues[0]
        batch_started_at = datetime.now(LISBON_TZ).isoformat()
        self.send_request_async(
            self.Output,
            CatalogBatch(venues=[venue], batch_started_at=batch_started_at),
        )


class ScoreClassifyProcess(BusinessProcess):
    """Computes popularity + heat level for every venue in a CatalogBatch.

    Owns validation/transform only -- no destination I/O here (that is
    PersistOperation's job). Recomputes popularity fresh for every venue on
    every call (POPU-06/R6); never reads PopHeat.Reading.
    """

    Persist = target("PersistOperation")

    def on_message(self, request: CatalogBatch):
        when = datetime.now(LISBON_TZ)
        observed_at = when.isoformat()

        readings = []
        for venue in request.venues:
            category = venue.get("category")
            popularity = compute_popularity(category, when)
            heat_level = classify_heat(category, popularity)
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
