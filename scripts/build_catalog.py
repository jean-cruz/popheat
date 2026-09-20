"""Build the PopHeat venue catalog from a live OpenStreetMap Overpass query.

Standalone stdlib-only CLI script (D-10). Reads bounding-box/amenity/endpoint
parameters from a config file (never hardcoded, D-13), queries the public
Overpass API for eligible amenity-tagged places within the configured
bounding box, discards places missing required fields, maps each surviving
element to a minimal public-facing venue record, and writes the result to
disk atomically. See specs/venue-sourcing.spec and
specs/ingestion-pipeline.spec for the business rules this implements.
"""

import argparse
import decimal
import json
import os
import socket
import sys
import tempfile
import urllib.error
import urllib.request

DEFAULT_CONFIG_PATH = "config/catalog_build.json"
RAW_SNAPSHOT_PATH = "data/venues.raw.json"
CATALOG_PATH = "data/venues.json"

REQUIRED_CONFIG_KEYS = (
    "bounding_box",
    "amenity_allowlist",
    "overpass_endpoint",
    "request_timeout_seconds",
    "overpass_timeout_seconds",
    "max_response_bytes",
)

REQUIRED_BBOX_KEYS = ("south", "west", "north", "east")


class ConfigError(Exception):
    """Raised when the build config file is missing or malformed."""


class OverpassFetchError(Exception):
    """Raised when the Overpass API request fails, times out, or the
    response cannot be parsed as JSON within the configured byte budget."""


def load_config(path):
    """Load and validate the catalog build config.

    Raises ConfigError with a clear message when the file is absent or any
    of the 6 required top-level keys is missing.
    """
    if not os.path.isfile(path):
        raise ConfigError(f"Config file not found: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Config file at {path} is not valid JSON: {e}") from e

    for key in REQUIRED_CONFIG_KEYS:
        if key not in config:
            raise ConfigError(
                f"Config file at {path} is missing required key: {key}"
            )

    bbox = config["bounding_box"]
    for key in REQUIRED_BBOX_KEYS:
        if not isinstance(bbox, dict) or key not in bbox:
            raise ConfigError(
                f"Config file at {path} bounding_box is missing required key: {key}"
            )

    return config


def build_overpass_query(config):
    """Build the Overpass QL query string scoped to the config's amenity
    allowlist and bounding box — never hardcoded (VENU-01/VENU-03)."""
    bbox = config["bounding_box"]
    allowlist = config["amenity_allowlist"]
    timeout = config["overpass_timeout_seconds"]

    amenity_regex = "^(" + "|".join(allowlist) + ")$"
    bbox_str = f"{bbox['south']},{bbox['west']},{bbox['north']},{bbox['east']}"

    return (
        f'[out:json][timeout:{timeout}];'
        f'nwr["amenity"~"{amenity_regex}"]({bbox_str});'
        f"out center;"
    )


def fetch_overpass(query, endpoint, request_timeout, max_bytes):
    """POST the Overpass QL query to endpoint and return the parsed JSON
    response. Reads at most max_bytes + 1 bytes before parsing to bound
    memory use, and wraps any network/parse failure in OverpassFetchError."""
    data = query.encode("utf-8")
    # overpass-api.de rejects requests lacking a descriptive User-Agent
    # (returns HTTP 406 for urllib's default "Python-urllib/x.y" UA) —
    # a real-world constraint of the live public endpoint, not documented
    # in the plan but required for any successful live call.
    headers = {"User-Agent": "PopHeat-CatalogBuilder/1.0 (+https://github.com/popheat)"}
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            body = response.read(max_bytes + 1)
    except (urllib.error.URLError, socket.timeout) as e:
        raise OverpassFetchError(f"Overpass request failed: {e}") from e

    if len(body) > max_bytes:
        raise OverpassFetchError(
            f"Overpass response exceeded max_response_bytes ({max_bytes})"
        )

    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise OverpassFetchError(f"Overpass response is not valid JSON: {e}") from e


def derive_id(element):
    """Derive a stable venue identifier from the OSM element type + id."""
    return f"{element['type']}/{element['id']}"


def map_element_to_venue(element, allowlist):
    """Map a raw Overpass element to a minimal venue record, or None if the
    element is missing a required field or its amenity is not in allowlist
    (VENU-02).

    The allowlist check here is local defense-in-depth: server-side
    filtering already happens via the regex built in build_overpass_query,
    but this guards against that filter ever diverging from allowlist or
    an Overpass API quirk returning tag-adjacent elements.

    Returns a dict with EXACTLY the keys: id, name, category, lat, lon.
    Never copies `tags` wholesale or contributor metadata (user/uid/
    changeset) — only the 5 whitelisted fields reach the output.
    """
    tags = element.get("tags", {})
    name = tags.get("name")
    category = tags.get("amenity")

    if name is None or str(name).strip() == "":
        return None

    if category is None or category not in allowlist:
        return None

    if "lat" in element and "lon" in element:
        lat = element["lat"]
        lon = element["lon"]
    elif "center" in element:
        lat = element["center"]["lat"]
        lon = element["center"]["lon"]
    else:
        return None

    return {
        "id": derive_id(element),
        "name": name,
        "category": category,
        "lat": lat,
        "lon": lon,
    }


def round5(value):
    """Round value to exactly 5 decimal places using explicit round-half-up
    (VENU-04 dedup key precision). Deliberately does NOT use Python's native
    round(), which applies round-half-to-even on floats and is subject to
    binary representation error; decimal.Decimal(str(value)) preserves the
    value's decimal string form before rounding."""
    return float(
        decimal.Decimal(str(value)).quantize(
            decimal.Decimal("0.00001"), rounding=decimal.ROUND_HALF_UP
        )
    )


def dedupe_venues(venues):
    """Drop duplicate venues: a venue is a duplicate of an earlier one if it
    shares the same exact `name` string and the same (lat, lon) rounded to 5
    decimal places (R4). Iterates in input order, keeps only the FIRST
    occurrence of each (name, round5(lat), round5(lon)) key, and preserves
    the relative order of survivors — no sorting."""
    seen = set()
    result = []
    for venue in venues:
        key = (venue["name"], round5(venue["lat"]), round5(venue["lon"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(venue)
    return result


def write_json_atomic(path, data):
    """Write data as JSON to path atomically: write to a temp file in the
    same directory, then os.replace() onto the final path. Ensures an
    interrupted write can never leave a partially-written file (D-05)."""
    parent_dir = os.path.dirname(path) or "."
    os.makedirs(parent_dir, exist_ok=True)

    tmp = tempfile.NamedTemporaryFile(
        mode="w", dir=parent_dir, delete=False, encoding="utf-8"
    )
    try:
        json.dump(data, tmp)
        tmp.close()
        os.replace(tmp.name, path)
    except BaseException:
        tmp.close()
        if os.path.exists(tmp.name):
            os.remove(tmp.name)
        raise


def run(config_path, fetch_fn=fetch_overpass, catalog_path=CATALOG_PATH, raw_path=RAW_SNAPSHOT_PATH):
    """Run the full build pipeline: load config, build the query, fetch via
    fetch_fn, map/filter/dedupe, and write raw + catalog output.

    fetch_fn/catalog_path/raw_path exist SPECIFICALLY so tests can substitute
    a fake fetch function and temp-directory paths without touching the
    network or the real data/ directory. Returns an int exit code: 0 on
    success, 1 on config or fetch failure (VENU-06 empty/failure semantics).

    A successful zero-match Overpass query is NOT an error: it writes an
    empty catalog and returns 0 (VENU-06 empty). A failed fetch leaves
    whatever is already at catalog_path untouched and returns non-zero
    (D-05). Each successful call fully overwrites catalog_path via
    write_json_atomic - no merge with prior content, no confirmation (D-12).
    """
    try:
        config = load_config(config_path)
    except ConfigError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    query = build_overpass_query(config)

    try:
        response = fetch_fn(
            query,
            config["overpass_endpoint"],
            config["request_timeout_seconds"],
            config["max_response_bytes"],
        )
        if "elements" not in response:
            raise OverpassFetchError(
                "Overpass response missing 'elements' "
                f"(remark: {response.get('remark', 'none')})"
            )
    except OverpassFetchError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    write_json_atomic(raw_path, response)

    elements = response["elements"]
    fetched_count = len(elements)

    venues = []
    dropped_count = 0
    for element in elements:
        venue = map_element_to_venue(element, config["amenity_allowlist"])
        if venue is None:
            dropped_count += 1
        else:
            venues.append(venue)

    deduped_venues = dedupe_venues(venues)
    duplicate_count = len(venues) - len(deduped_venues)

    write_json_atomic(catalog_path, deduped_venues)

    print(
        f"Fetched: {fetched_count}, dropped (missing field): {dropped_count}, "
        f"dropped (duplicate): {duplicate_count}, final catalog: {len(deduped_venues)}"
    )
    return 0


def main():
    parser = argparse.ArgumentParser(description="Build the PopHeat venue catalog from OpenStreetMap.")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to the catalog build config JSON file")
    args = parser.parse_args()
    return run(args.config)


if __name__ == "__main__":
    sys.exit(main())
