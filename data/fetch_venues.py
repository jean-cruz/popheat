"""Regenerates data/venues.json with real venues from OpenStreetMap (Overpass
API) inside BBOX. Free, no API key required. To change city, edit BBOX below
and rerun (`python3 data/fetch_venues.py`)."""
import urllib.request, urllib.parse, json, sys, time, pathlib

BBOX = (-23.575, -46.675, -23.545, -46.635)  # Sao Paulo: Paulista / Jardins / Pinheiros / Vila Madalena
CATEGORIES = "bar|pub|restaurant|cafe|fast_food|nightclub"
OUTPUT_FILE = pathlib.Path(__file__).parent / "venues.json"

query = f"""
[out:json][timeout:25];
node["amenity"~"{CATEGORIES}"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});
out body;
"""

url = "https://overpass-api.de/api/interpreter"
data = urllib.parse.urlencode({"data": query}).encode()

for attempt in range(3):
    try:
        req = urllib.request.Request(url, data=data, headers={
            "User-Agent": "PopHeat-PyProd-Contest/1.0 (contact: jeansc@outlook.com)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=40) as resp:
            result = json.load(resp)
        break
    except Exception as e:
        print(f"attempt {attempt} failed: {e}", file=sys.stderr)
        time.sleep(5)
else:
    raise SystemExit("all attempts failed")

venues = []
seen = set()
for el in result.get("elements", []):
    tags = el.get("tags", {})
    name = tags.get("name")
    lat, lon = el.get("lat"), el.get("lon")
    amenity = tags.get("amenity")
    if not (name and lat and lon and amenity):
        continue
    key = (name, round(lat, 5), round(lon, 5))
    if key in seen:
        continue
    seen.add(key)
    venues.append({
        "venue_id": f"osm-{el['id']}",
        "name": name,
        "category": amenity,
        "lat": lat,
        "lon": lon,
    })

print(f"Collected {len(venues)} named venues", file=sys.stderr)
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(venues, f, ensure_ascii=False, indent=2)
