"""Pure, IRIS-independent scoring/classification/batching math for PopHeat.

Deliberately imports NOTHING from `iop`/`iris` -- must be importable and
testable with plain `python3` (Plan 02-02, Task 1). Everything an IRIS
Interoperability component needs from the popularity/heat-classification/
batching domain lives here; `popheat_pipeline/components.py` imports from
this module instead of duplicating the logic.

See specs/popularity-model.spec, specs/heat-classification.spec, and
specs/ingestion-pipeline.spec for the business rules implemented here.
"""

import json
import math
import os
import random

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


def compute_popularity(category, when) -> float:
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

# Spec-default thresholds (heat-classification.spec R1/R2), used as the
# fallback whenever config/heat_thresholds.json is missing, malformed, or
# out of range (HEAT-04) -- and as the literal starter content for that file.
DEFAULT_THRESHOLDS = {
    "nightlife": {"CRITICO": 0.60, "ALTO": 0.40, "MEDIO": 0.20},
    "daytime": {"CRITICO": 0.75, "ALTO": 0.50, "MEDIO": 0.25},
}

# Evaluated highest-threshold-first (R3): first matching rule wins.
_LEVELS_HIGH_TO_LOW = ("CRITICO", "ALTO", "MEDIO")

_REQUIRED_THRESHOLD_GROUPS = ("nightlife", "daytime")
_REQUIRED_THRESHOLD_LEVELS = ("CRITICO", "ALTO", "MEDIO")


def _is_number(value) -> bool:
    """True for int/float, explicitly excluding bool (a subclass of int in
    Python but never a valid threshold value) -- mirrors
    scripts/build_catalog.py's `_is_number` convention."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _thresholds_valid(thresholds) -> bool:
    """True iff `thresholds` has exactly the shape DEFAULT_THRESHOLDS has:
    both groups present, all three levels present per group, every value a
    number in [0, 1]. Used by both load_thresholds (HEAT-04 fallback gate)
    and classify_heat (defensive re-check, matching the try/except-returns-
    BAIXO contract for a shape it wasn't handed via load_thresholds)."""
    if not isinstance(thresholds, dict):
        return False
    for group in _REQUIRED_THRESHOLD_GROUPS:
        group_values = thresholds.get(group)
        if not isinstance(group_values, dict):
            return False
        for level in _REQUIRED_THRESHOLD_LEVELS:
            if level not in group_values:
                return False
            value = group_values[level]
            if not _is_number(value) or value < 0 or value > 1:
                return False
    return True


def load_thresholds(path):
    """Load heat-level thresholds from `path` (HEAT-03: config, not code).

    Returns the file's own values when `path` exists, is valid JSON, and
    every threshold value is a number in [0, 1] with both required groups
    (`nightlife`/`daytime`) and all three levels
    (`CRITICO`/`ALTO`/`MEDIO`) present. On ANY missing-file, JSON-decode
    error, or out-of-range/missing-key value, returns DEFAULT_THRESHOLDS
    instead -- never raises to the caller (HEAT-04: a corrupted config can
    never take down a batch cycle). Intentionally does not log here -- the
    caller (which has host logging methods) logs if it cares; this module
    stays IRIS-independent.
    """
    if not os.path.isfile(path):
        return DEFAULT_THRESHOLDS

    try:
        with open(path, "r", encoding="utf-8") as f:
            thresholds = json.load(f)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return DEFAULT_THRESHOLDS

    if not _thresholds_valid(thresholds):
        return DEFAULT_THRESHOLDS

    return thresholds


def classify_heat(category, popularity, thresholds) -> str:
    """Classify a popularity score into BAIXO/MEDIO/ALTO/CRITICO (R1-R5).

    Nightlife categories (bar/pub/nightclub) use the `thresholds["nightlife"]`
    scale; every other category uses `thresholds["daytime"]` (R1/R2).
    `thresholds` is a caller-supplied dict (not a module constant) so callers
    control freshness -- Plan 02-02's ScoreClassifyProcess calls
    `load_thresholds(...)` fresh on every batch (HEAT-03/D-10). Defaults to
    BAIXO -- including when `thresholds` is missing a required key/group or
    classification otherwise fails for any reason (HEAT-04/R5) -- rather
    than leaving a reading unlabeled or raising.
    """
    try:
        group = "nightlife" if category in NIGHTLIFE_CATEGORIES else "daytime"
        scale = thresholds[group]
        for level in _LEVELS_HIGH_TO_LOW:
            if popularity >= scale[level]:
                return level
        return "BAIXO"
    except Exception:
        return "BAIXO"


# ---------------------------------------------------------------------------
# Batching (specs/ingestion-pipeline.spec R1, R2)
# ---------------------------------------------------------------------------


def select_batch(catalog, cursor, size=150):
    """Select the next `size`-item batch from `catalog` via circular (modulo)
    indexing starting at `cursor` (INGE-02, INGE-03).

    Returns `(batch, next_cursor)`. `batch` always has exactly `size` items
    (repeating early catalog items as needed once the cursor wraps past the
    end -- true circular wrap, even mid-batch), EXCEPT when `catalog` is
    empty, in which case `batch` is `[]` rather than raising
    ZeroDivisionError/IndexError from the modulo operation. `next_cursor` is
    `(cursor + size) % len(catalog)` -- the walk-and-wrap semantics that
    guarantee the full catalog is revisited on a regular cycle (R2).
    """
    n = len(catalog)
    if n == 0:
        return [], 0

    batch = [catalog[(cursor + i) % n] for i in range(size)]
    next_cursor = (cursor + size) % n
    return batch, next_cursor
