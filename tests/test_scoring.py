"""Unit tests for popheat_pipeline/scoring.py's pure functions.

Covers select_batch (circular batching, wrap boundary, empty-catalog guard),
load_thresholds (config override + safe-default fallback), compute_popularity
(range across categories/hours), classify_heat (all 4 labels + BAIXO default
on malformed thresholds), and compute_throughput (zero-safe division) --
all offline, no IRIS/network dependency. Mirrors tests/test_build_catalog.py's
style: `class ...(unittest.TestCase)`, one test method per behavior.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from popheat_pipeline.scoring import (
    CATEGORY_CURVES,
    DEFAULT_THRESHOLDS,
    circular_distance,
    classify_heat,
    compute_popularity,
    load_thresholds,
    select_batch,
)

LISBON_TZ = ZoneInfo("Europe/Lisbon")


def _make_catalog(n):
    return [{"id": f"node/{i}", "name": f"Venue {i}"} for i in range(n)]


class SelectBatchTests(unittest.TestCase):
    """INGE-02, INGE-03: circular (modulo) batch selection over the catalog."""

    def test_basic_batch_no_wrap(self):
        catalog = _make_catalog(906)
        batch, next_cursor = select_batch(catalog, 0, 150)
        self.assertEqual(len(batch), 150)
        self.assertEqual(batch, catalog[0:150])
        self.assertEqual(next_cursor, 150)

    def test_wrap_boundary_mid_batch(self):
        """Acceptance criteria: cursor=900, size=150 on a 906-length catalog
        wraps mid-batch -- last 6 items are catalog[900:906], first 144 items
        are catalog[0:144], next cursor is 144."""
        catalog = _make_catalog(906)
        batch, next_cursor = select_batch(catalog, 900, 150)
        self.assertEqual(len(batch), 150)
        self.assertEqual(batch[:6], catalog[900:906])
        self.assertEqual(batch[6:], catalog[0:144])
        self.assertEqual(next_cursor, 144)

    def test_two_calls_in_a_row_wrap_correctly(self):
        catalog = _make_catalog(906)
        cursor = 900
        batch1, cursor = select_batch(catalog, cursor, 150)
        self.assertEqual(cursor, 144)
        batch2, cursor = select_batch(catalog, cursor, 150)
        self.assertEqual(len(batch2), 150)
        self.assertEqual(batch2, catalog[144:294])

    def test_short_catalog_repeats_items_true_circular_wrap(self):
        """select_batch on a catalog shorter than size (length 6) still
        returns exactly `size` items, repeating early items as needed."""
        catalog = _make_catalog(6)
        batch, next_cursor = select_batch(catalog, 0, 150)
        self.assertEqual(len(batch), 150)
        # 150 = 25 * 6 exactly, so the batch is 25 full repeats of the catalog.
        self.assertEqual(batch, catalog * 25)
        self.assertEqual(next_cursor, 0)

    def test_empty_catalog_returns_empty_batch_no_crash(self):
        """select_batch on an empty catalog returns [] rather than raising
        ZeroDivisionError/IndexError from the modulo operation."""
        batch, next_cursor = select_batch([], 0, 150)
        self.assertEqual(batch, [])
        self.assertEqual(next_cursor, 0)

    def test_full_cycle_revisits_every_venue(self):
        """R2: walking the full catalog in fixed batches from cursor 0
        eventually revisits every venue starting a new cycle at cursor 0
        again (906 is not a multiple of 150, so cursor cycles through the
        full catalog length before returning to 0)."""
        catalog = _make_catalog(906)
        cursor = 0
        seen_cursors = set()
        for _ in range(1000):
            if cursor in seen_cursors:
                break
            seen_cursors.add(cursor)
            _, cursor = select_batch(catalog, cursor, 150)
        self.assertEqual(cursor, 0)


class LoadThresholdsTests(unittest.TestCase):
    """HEAT-03, HEAT-04: config-driven thresholds with safe defaults."""

    def test_missing_file_returns_defaults(self):
        result = load_thresholds("/nonexistent/path/heat_thresholds.json")
        self.assertEqual(result, DEFAULT_THRESHOLDS)

    def test_malformed_json_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "heat_thresholds.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not valid json")
            result = load_thresholds(path)
            self.assertEqual(result, DEFAULT_THRESHOLDS)

    def test_out_of_range_value_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "heat_thresholds.json")
            bad = {
                "nightlife": {"CRITICO": 1.5, "ALTO": 0.40, "MEDIO": 0.20},
                "daytime": {"CRITICO": 0.75, "ALTO": 0.50, "MEDIO": 0.25},
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bad, f)
            result = load_thresholds(path)
            self.assertEqual(result, DEFAULT_THRESHOLDS)

    def test_missing_key_returns_defaults(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "heat_thresholds.json")
            bad = {"nightlife": {"CRITICO": 0.60, "ALTO": 0.40}}  # missing MEDIO, daytime
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bad, f)
            result = load_thresholds(path)
            self.assertEqual(result, DEFAULT_THRESHOLDS)

    def test_valid_file_overrides_defaults(self):
        """HEAT-03: the config file's own values actually override defaults."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "heat_thresholds.json")
            custom = {
                "nightlife": {"CRITICO": 0.65, "ALTO": 0.45, "MEDIO": 0.25},
                "daytime": {"CRITICO": 0.80, "ALTO": 0.55, "MEDIO": 0.30},
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(custom, f)
            result = load_thresholds(path)
            self.assertEqual(result, custom)
            self.assertNotEqual(result, DEFAULT_THRESHOLDS)


class ComputePopularityTests(unittest.TestCase):
    """POPU-01 through POPU-05: range + shape sanity across categories/hours."""

    def test_always_within_clamp_range(self):
        for category in list(CATEGORY_CURVES.keys()) + ["unknown_category"]:
            for hour in range(0, 24):
                when = datetime(2026, 9, 21, hour, 0, tzinfo=LISBON_TZ)  # a Monday
                popularity = compute_popularity(category, when)
                with self.subTest(category=category, hour=hour):
                    self.assertGreaterEqual(popularity, 0.02)
                    self.assertLessEqual(popularity, 0.98)

    def test_weekend_and_weekday_both_within_range(self):
        # 2026-09-19 is a Saturday (weekend boost applies).
        for day in (19, 21):
            when = datetime(2026, 9, day, 22, 0, tzinfo=LISBON_TZ)
            popularity = compute_popularity("nightclub", when)
            self.assertGreaterEqual(popularity, 0.02)
            self.assertLessEqual(popularity, 0.98)


class ClassifyHeatTests(unittest.TestCase):
    """HEAT-01 through HEAT-05: nightlife vs daytime thresholds, BAIXO default."""

    def test_returns_all_four_labels(self):
        thresholds = DEFAULT_THRESHOLDS
        cases = [
            ("bar", 0.65, "CRITICO"),
            ("bar", 0.45, "ALTO"),
            ("bar", 0.25, "MEDIO"),
            ("bar", 0.05, "BAIXO"),
        ]
        for category, popularity, expected in cases:
            with self.subTest(category=category, popularity=popularity):
                self.assertEqual(classify_heat(category, popularity, thresholds), expected)

    def test_daytime_category_uses_daytime_scale(self):
        thresholds = DEFAULT_THRESHOLDS
        # 0.65 is CRITICO on the nightlife scale but only ALTO on daytime.
        self.assertEqual(classify_heat("cafe", 0.65, thresholds), "ALTO")

    def test_missing_required_key_defaults_to_baixo(self):
        broken_thresholds = {"nightlife": {"CRITICO": 0.60}}  # missing ALTO/MEDIO/daytime
        result = classify_heat("bar", 0.99, broken_thresholds)
        self.assertEqual(result, "BAIXO")

    def test_empty_thresholds_defaults_to_baixo(self):
        self.assertEqual(classify_heat("cafe", 0.99, {}), "BAIXO")


class CircularDistanceTests(unittest.TestCase):
    def test_midnight_wrap(self):
        self.assertEqual(circular_distance(23, 1), 2)

    def test_same_hour(self):
        self.assertEqual(circular_distance(10, 10), 0)


if __name__ == "__main__":
    unittest.main()
