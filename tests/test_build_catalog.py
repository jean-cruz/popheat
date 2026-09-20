"""Unit tests for scripts/build_catalog.py's pure functions.

Covers query construction, field mapping/filtering, ID derivation, and
config validation — all offline, no network access.
"""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from scripts.build_catalog import (
    ConfigError,
    OverpassFetchError,
    build_overpass_query,
    dedupe_venues,
    derive_id,
    load_config,
    map_element_to_venue,
    round5,
    run,
)

VALID_CONFIG = {
    "bounding_box": {
        "south": 41.1390,
        "west": -8.6200,
        "north": 41.1510,
        "east": -8.6020,
    },
    "amenity_allowlist": ["bar", "pub", "restaurant", "cafe", "fast_food", "nightclub"],
    "overpass_endpoint": "https://overpass-api.de/api/interpreter",
    "request_timeout_seconds": 30,
    "overpass_timeout_seconds": 25,
    "max_response_bytes": 20000000,
}


class BuildCatalogTests(unittest.TestCase):
    def test_query_includes_bbox_and_allowlist(self):
        query = build_overpass_query(VALID_CONFIG)
        bbox = VALID_CONFIG["bounding_box"]
        for value in (bbox["south"], bbox["west"], bbox["north"], bbox["east"]):
            self.assertIn(str(value), query)
        self.assertIn("(bar|pub|restaurant|cafe|fast_food|nightclub)", query)

    def test_query_has_no_wildcard_amenity_filter(self):
        query = build_overpass_query(VALID_CONFIG)
        self.assertNotIn('["amenity"]', query)

    def test_map_element_drops_missing_name(self):
        base_element = {
            "type": "node",
            "id": 1,
            "lat": 41.14,
            "lon": -8.61,
            "tags": {"amenity": "bar"},
        }
        cases = {
            "absent_name": {},
            "empty_name": {"name": ""},
            "whitespace_name": {"name": "   "},
        }
        for case_name, extra_tags in cases.items():
            with self.subTest(case=case_name):
                element = dict(base_element)
                element["tags"] = {**base_element["tags"], **extra_tags}
                result = map_element_to_venue(element, VALID_CONFIG["amenity_allowlist"])
                self.assertIsNone(result)

    def test_map_element_drops_missing_lat_lon(self):
        element = {
            "type": "node",
            "id": 2,
            "tags": {"amenity": "bar", "name": "Test Bar"},
        }
        result = map_element_to_venue(element, VALID_CONFIG["amenity_allowlist"])
        self.assertIsNone(result)

    def test_map_element_drops_missing_amenity(self):
        element = {
            "type": "node",
            "id": 3,
            "lat": 41.14,
            "lon": -8.61,
            "tags": {"name": "Test Bar"},
        }
        result = map_element_to_venue(element, VALID_CONFIG["amenity_allowlist"])
        self.assertIsNone(result)

    def test_map_element_whitelists_fields_only(self):
        element = {
            "type": "node",
            "id": 4,
            "lat": 41.14,
            "lon": -8.61,
            "user": "some_osm_editor",
            "uid": 12345,
            "changeset": 67890,
            "tags": {
                "amenity": "bar",
                "name": "Test Bar",
                "contact:phone": "+351123456789",
            },
        }
        result = map_element_to_venue(element, VALID_CONFIG["amenity_allowlist"])
        self.assertIsNotNone(result)
        self.assertEqual(set(result.keys()), {"id", "name", "category", "lat", "lon"})
        self.assertEqual(result["name"], "Test Bar")
        self.assertEqual(result["category"], "bar")

    def test_derive_id_node_and_way(self):
        node_element = {"type": "node", "id": 123}
        way_element = {"type": "way", "id": 456}
        self.assertEqual(derive_id(node_element), "node/123")
        self.assertEqual(derive_id(way_element), "way/456")

    def test_load_config_missing_file_raises(self):
        with self.assertRaises(ConfigError):
            load_config("/nonexistent/path/catalog_build.json")

    def test_load_config_missing_key_raises(self):
        incomplete_config = dict(VALID_CONFIG)
        del incomplete_config["amenity_allowlist"]
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = os.path.join(tmp_dir, "catalog_build.json")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(incomplete_config, f)
            with self.assertRaises(ConfigError):
                load_config(config_path)

    def test_map_element_empty_list(self):
        elements = []
        results = [map_element_to_venue(e, VALID_CONFIG["amenity_allowlist"]) for e in elements]
        self.assertEqual(results, [])

    def test_output_order_preserves_input_order(self):
        element_a = {
            "type": "node",
            "id": 10,
            "lat": 41.14,
            "lon": -8.61,
            "tags": {"amenity": "bar", "name": "Bar A"},
        }
        element_b = {
            "type": "node",
            "id": 20,
            "lat": 41.15,
            "lon": -8.62,
            "tags": {"amenity": "cafe", "name": "Cafe B"},
        }
        results = [
            map_element_to_venue(e, VALID_CONFIG["amenity_allowlist"])
            for e in (element_a, element_b)
        ]
        self.assertEqual(results[0]["name"], "Bar A")
        self.assertEqual(results[1]["name"], "Cafe B")

    def test_round5_half_up_tie(self):
        self.assertEqual(round5(41.123455), 41.12346)

    def test_dedupe_empty_and_single(self):
        self.assertEqual(dedupe_venues([]), [])
        venue = {"id": "node/1", "name": "Bar A", "category": "bar", "lat": 41.14, "lon": -8.61}
        self.assertEqual(dedupe_venues([venue]), [venue])

    def test_dedupe_drops_boundary_duplicate(self):
        first = {"id": "node/1", "name": "Bar A", "category": "bar", "lat": 41.140551, "lon": -8.61}
        second = {"id": "node/2", "name": "Bar A", "category": "bar", "lat": 41.140554, "lon": -8.61}
        result = dedupe_venues([first, second])
        self.assertEqual(result, [first])

    def test_dedupe_case_sensitive_names_not_merged(self):
        first = {"id": "node/1", "name": "Café Aroma", "category": "cafe", "lat": 41.14, "lon": -8.61}
        second = {"id": "node/2", "name": "café aroma", "category": "cafe", "lat": 41.14, "lon": -8.61}
        result = dedupe_venues([first, second])
        self.assertEqual(result, [first, second])

    def test_dedupe_keeps_first_id_on_collision(self):
        first = {"id": "node/1", "name": "Bar A", "category": "bar", "lat": 41.14, "lon": -8.61}
        second = {"id": "node/2", "name": "Bar A", "category": "bar", "lat": 41.14, "lon": -8.61}
        result = dedupe_venues([first, second])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "node/1")

    def test_dedupe_preserves_survivor_order(self):
        v0 = {"id": "node/1", "name": "Bar A", "category": "bar", "lat": 41.14, "lon": -8.61}
        v1 = {"id": "node/2", "name": "Cafe B", "category": "cafe", "lat": 41.15, "lon": -8.62}
        v2 = {"id": "node/3", "name": "Bar A", "category": "bar", "lat": 41.14, "lon": -8.61}
        result = dedupe_venues([v0, v1, v2])
        self.assertEqual(result, [v0, v1])

    def _write_config(self, tmp_dir):
        config_path = os.path.join(tmp_dir, "catalog_build.json")
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(VALID_CONFIG, f)
        return config_path

    def test_run_empty_overpass_result_writes_empty_catalog_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = self._write_config(tmp_dir)
            catalog_path = os.path.join(tmp_dir, "venues.json")
            raw_path = os.path.join(tmp_dir, "venues.raw.json")

            def fake_fetch_fn(query, endpoint, request_timeout, max_bytes):
                return {"elements": []}

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = run(
                    config_path,
                    fetch_fn=fake_fetch_fn,
                    catalog_path=catalog_path,
                    raw_path=raw_path,
                )

            self.assertEqual(exit_code, 0)
            with open(catalog_path, "r", encoding="utf-8") as f:
                self.assertEqual(json.load(f), [])
            self.assertIn("final catalog: 0", stdout.getvalue())

    def test_run_fetch_failure_leaves_existing_catalog_untouched_and_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = self._write_config(tmp_dir)
            catalog_path = os.path.join(tmp_dir, "venues.json")
            raw_path = os.path.join(tmp_dir, "venues.raw.json")

            existing_bytes = b'[{"id": "node/1", "name": "Existing Bar", "category": "bar", "lat": 41.14, "lon": -8.61}]'
            with open(catalog_path, "wb") as f:
                f.write(existing_bytes)

            def failing_fetch_fn(query, endpoint, request_timeout, max_bytes):
                raise OverpassFetchError("simulated failure")

            exit_code = run(
                config_path,
                fetch_fn=failing_fetch_fn,
                catalog_path=catalog_path,
                raw_path=raw_path,
            )

            self.assertNotEqual(exit_code, 0)
            with open(catalog_path, "rb") as f:
                self.assertEqual(f.read(), existing_bytes)

    def test_run_missing_elements_key_treated_as_failure_not_zero_match(self):
        """CR-01 regression: a 200-OK Overpass response whose JSON body
        carries a `remark` (soft error/timeout) instead of an `elements`
        list must be treated as a fetch failure — NOT as a genuine
        zero-match success — and must leave any existing catalog untouched
        (VENU-06 failure semantics, D-05)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = self._write_config(tmp_dir)
            catalog_path = os.path.join(tmp_dir, "venues.json")
            raw_path = os.path.join(tmp_dir, "venues.raw.json")

            existing_bytes = b'[{"id": "node/1", "name": "Existing Bar", "category": "bar", "lat": 41.14, "lon": -8.61}]'
            with open(catalog_path, "wb") as f:
                f.write(existing_bytes)

            def soft_failure_fetch_fn(query, endpoint, request_timeout, max_bytes):
                return {"remark": "runtime error: Query timed out"}

            exit_code = run(
                config_path,
                fetch_fn=soft_failure_fetch_fn,
                catalog_path=catalog_path,
                raw_path=raw_path,
            )

            self.assertNotEqual(exit_code, 0)
            with open(catalog_path, "rb") as f:
                self.assertEqual(f.read(), existing_bytes)
            self.assertFalse(os.path.exists(raw_path))

    def test_run_second_call_fully_overwrites_first(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = self._write_config(tmp_dir)
            catalog_path = os.path.join(tmp_dir, "venues.json")
            raw_path = os.path.join(tmp_dir, "venues.raw.json")

            element_a = {
                "type": "node",
                "id": 1,
                "lat": 41.14,
                "lon": -8.61,
                "tags": {"amenity": "bar", "name": "Venue A"},
            }
            element_b = {
                "type": "node",
                "id": 2,
                "lat": 41.15,
                "lon": -8.62,
                "tags": {"amenity": "cafe", "name": "Venue B"},
            }

            def fetch_a(query, endpoint, request_timeout, max_bytes):
                return {"elements": [element_a]}

            def fetch_b(query, endpoint, request_timeout, max_bytes):
                return {"elements": [element_b]}

            run(config_path, fetch_fn=fetch_a, catalog_path=catalog_path, raw_path=raw_path)
            run(config_path, fetch_fn=fetch_b, catalog_path=catalog_path, raw_path=raw_path)

            with open(catalog_path, "r", encoding="utf-8") as f:
                catalog = json.load(f)
            self.assertEqual(len(catalog), 1)
            self.assertEqual(catalog[0]["name"], "Venue B")


if __name__ == "__main__":
    unittest.main()
