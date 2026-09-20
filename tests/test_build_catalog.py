"""Unit tests for scripts/build_catalog.py's pure functions.

Covers query construction, field mapping/filtering, ID derivation, and
config validation — all offline, no network access.
"""

import json
import os
import tempfile
import unittest

from scripts.build_catalog import (
    ConfigError,
    build_overpass_query,
    derive_id,
    load_config,
    map_element_to_venue,
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


if __name__ == "__main__":
    unittest.main()
