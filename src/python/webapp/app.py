"""
PopHeat dashboard - a Flask WSGI app hosted directly by InterSystems IRIS
(Security.Applications DispatchClass = %SYS.Python.WSGI).

Reads the venue readings produced by the PopHeat PyProd production straight
from IRIS SQL (in-process, via the embedded `iris` module - no network hop)
and renders a live heatmap + a small telemetry panel.
"""
from datetime import datetime

from flask import Flask, jsonify, Response

import iris

app = Flask(__name__)

LATEST_PER_VENUE_SQL = """
SELECT VenueId, name, category, lat, lon, popularity, HeatLevel, ObservedAt FROM (
  SELECT VenueId, name, category, lat, lon, popularity, HeatLevel, ObservedAt,
         ROW_NUMBER() OVER (PARTITION BY VenueId ORDER BY %ID DESC) AS rn
  FROM PopHeat.VenueReading
) WHERE rn = 1
"""

STATS_SQL = """
SELECT HeatLevel, COUNT(*) AS cnt FROM (
  SELECT VenueId, HeatLevel,
         ROW_NUMBER() OVER (PARTITION BY VenueId ORDER BY %ID DESC) AS rn
  FROM PopHeat.VenueReading
) WHERE rn = 1
GROUP BY HeatLevel
"""


def _ensure_namespace():
    iris.system.Process.SetNamespace("POPHEAT")


@app.route("/api/venues")
def api_venues():
    _ensure_namespace()
    rows = iris.sql.exec(LATEST_PER_VENUE_SQL)
    venues = [
        {
            "venue_id": r[0],
            "name": r[1],
            "category": r[2],
            "lat": r[3],
            "lon": r[4],
            "popularity": r[5],
            "heat_level": r[6],
            "observed_at": r[7],
        }
        for r in rows
    ]
    return jsonify({"venues": venues, "count": len(venues), "generated_at": datetime.now().isoformat()})


@app.route("/api/stats")
def api_stats():
    """Telemetry endpoint: counts by heat level + total readings ingested."""
    _ensure_namespace()
    by_level = {r[0]: r[1] for r in iris.sql.exec(STATS_SQL)}
    total_readings = list(iris.sql.exec("SELECT COUNT(*) FROM PopHeat.VenueReading"))[0][0]
    prod_status = "unknown"
    try:
        running = iris.cls("Ens.Director").IsProductionRunning("PopHeat.PopHeatProduction")
        prod_status = "running" if running else "stopped"
    except Exception:
        pass
    return jsonify({
        "by_heat_level": by_level,
        "distinct_venues": sum(by_level.values()),
        "total_readings_ingested": total_readings,
        "production_status": prod_status,
        "generated_at": datetime.now().isoformat(),
    })


@app.route("/api/telemetry")
def api_telemetry():
    _ensure_namespace()
    rows = list(iris.sql.exec(
        "SELECT TOP 20 BatchSize, ElapsedSeconds, VenuesPerSecond, RecordedAt "
        "FROM PopHeat.BatchMetric ORDER BY %ID DESC"
    ))
    batches = [
        {"batch_size": r[0], "elapsed_seconds": r[1], "venues_per_second": r[2], "recorded_at": r[3]}
        for r in rows
    ]
    avg_throughput = round(sum(b["venues_per_second"] for b in batches) / len(batches), 1) if batches else 0
    return jsonify({"recent_batches": batches, "avg_venues_per_second": avg_throughput})


@app.route("/")
def index():
    return Response(INDEX_HTML, mimetype="text/html")


INDEX_HTML = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<title>PopHeat - Mapa de Calor de Sao Paulo</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<style>
  html, body { margin:0; padding:0; height:100%; font-family: -apple-system, Segoe UI, Roboto, sans-serif; }
  #map { position:absolute; top:56px; bottom:0; left:0; right:0; }
  header { height:56px; display:flex; align-items:center; gap:16px; padding:0 16px; background:#101828; color:#fff; }
  header h1 { font-size:16px; margin:0; font-weight:600; }
  header .stats { display:flex; gap:10px; font-size:12px; flex-wrap:wrap; }
  .pill { padding:3px 9px; border-radius:999px; background:#1f2937; }
  .pill b { font-variant-numeric: tabular-nums; }
  .legend { position:absolute; bottom:16px; left:16px; z-index:1000; background:rgba(16,24,40,0.9); color:#fff;
            padding:10px 14px; border-radius:8px; font-size:12px; line-height:1.6; }
  .dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }
  .updated { position:absolute; top:64px; right:16px; z-index:1000; background:rgba(16,24,40,0.85); color:#cbd5e1;
             padding:4px 10px; border-radius:6px; font-size:11px; }
</style>
</head>
<body>
<header>
  <h1>PopHeat &mdash; lugares mais cheios agora (Sao Paulo)</h1>
  <div class="stats" id="stats"></div>
</header>
<div id="map"></div>
<div class="updated" id="updated">carregando...</div>
<div class="legend">
  <div><span class="dot" style="background:#2563eb"></span>Baixo</div>
  <div><span class="dot" style="background:#eab308"></span>Medio</div>
  <div><span class="dot" style="background:#f97316"></span>Alto</div>
  <div><span class="dot" style="background:#dc2626"></span>Critico</div>
</div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
<script>
const COLORS = {BAIXO:'#2563eb', MEDIO:'#eab308', ALTO:'#f97316', CRITICO:'#dc2626'};

const map = L.map('map').setView([-23.5600, -46.6550], 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: '&copy; OpenStreetMap contributors'
}).addTo(map);

let heatLayer = L.heatLayer([], {radius: 22, blur: 18, maxZoom: 17}).addTo(map);
let markerLayer = L.layerGroup().addTo(map);

async function refresh() {
  try {
    const [vRes, sRes, tRes] = await Promise.all([fetch('api/venues'), fetch('api/stats'), fetch('api/telemetry')]);
    const vData = await vRes.json();
    const sData = await sRes.json();
    const tData = await tRes.json();

    const heatPoints = vData.venues.map(v => [v.lat, v.lon, Math.max(v.popularity, 0.05)]);
    heatLayer.setLatLngs(heatPoints);

    markerLayer.clearLayers();
    vData.venues
      .filter(v => v.heat_level === 'CRITICO' || v.heat_level === 'ALTO')
      .forEach(v => {
        L.circleMarker([v.lat, v.lon], {
          radius: v.heat_level === 'CRITICO' ? 7 : 5,
          color: COLORS[v.heat_level],
          fillColor: COLORS[v.heat_level],
          fillOpacity: 0.85,
          weight: 1,
        }).bindPopup(
          `<b>${v.name}</b><br>${v.category}<br>popularidade: ${v.popularity}<br>heat: ${v.heat_level}<br>${v.observed_at}`
        ).addTo(markerLayer);
      });

    const statsEl = document.getElementById('stats');
    const levels = ['BAIXO','MEDIO','ALTO','CRITICO'];
    statsEl.innerHTML = levels.map(l =>
      `<span class="pill"><span class="dot" style="background:${COLORS[l]}"></span>${l}: <b>${sData.by_heat_level[l] || 0}</b></span>`
    ).join('') + `<span class="pill">producao: <b>${sData.production_status}</b></span>` +
      `<span class="pill">leituras: <b>${sData.total_readings_ingested}</b></span>` +
      `<span class="pill">gravacao DB: <b>${tData.avg_venues_per_second}</b> locais/s</span>`;

    document.getElementById('updated').textContent =
      `${vData.count} locais - atualizado ${new Date(vData.generated_at).toLocaleTimeString('pt-BR')}`;
  } catch (e) {
    document.getElementById('updated').textContent = 'erro ao atualizar: ' + e;
  }
}

refresh();
setInterval(refresh, 10000);
</script>
</body>
</html>
"""
