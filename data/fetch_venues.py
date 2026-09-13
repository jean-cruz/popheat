import urllib.request, urllib.parse, json, sys, time

BBOX = (41.135, -8.635, 41.165, -8.580)  # Porto historic center + surroundings
CATEGORIES = "bar|pub|restaurant|cafe|fast_food|nightclub"

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
with open("/tmp/claude-1001/-home-jean-contest/0d4377b7-0c32-463d-9f59-08d01c3013d3/scratchpad/porto_venues.json", "w", encoding="utf-8") as f:
    json.dump(venues, f, ensure_ascii=False, indent=2)
