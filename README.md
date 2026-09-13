# PopHeat

A live crowdedness heatmap for the city of Porto, Portugal, built as a **pure-Python InterSystems IRIS Interoperability Production** using [PyProd](https://github.com/intersystems/pyprod).

Built for the **InterSystems Portuguese Community AI Programming Contest 2026** ([contest page](https://pt.community.intersystems.com/contests/current)), PyProd track.

![status](https://img.shields.io/badge/IRIS-2026.2-blue) ![license](https://img.shields.io/badge/license-MIT-green)

## What it does

PopHeat ingests ~1,500 real venues (bars, restaurants, cafés, pubs, nightclubs) in Porto, scores how crowded each one likely is right now, classifies that score through an IRIS **Business Rule**, persists it, and renders it as a live heatmap on a **Flask/WSGI** dashboard hosted directly by IRIS — refreshing every 10 seconds.

<p align="center"><em>(add a screenshot of the dashboard here before publishing)</em></p>

## Why the popularity score is synthetic, not scraped

The original idea was to use Google's "Popular Times" data. That turned out to be a dead end worth documenting:

- **Google** has no public API for Popular Times / live busyness. The only way to get it is by reverse-engineering internal Google Maps endpoints (the unofficial `populartimes` library) — fragile, and against Google's Terms of Service.
- **Foursquare Places API** looked like a legitimate alternative (it has an official `popularity` field), until we checked current pricing: as of June 2026 Foursquare cut the free tier to 500 Pro calls/month, and `popularity` is a **Premium** field billed from the very first call — no free tier at all.

So PopHeat uses:
- **Real venue data** (name, category, coordinates) from **OpenStreetMap** via the Overpass API — free, no key, no rate-limit surprises. See `data/fetch_venues.py`.
- A **transparent, documented synthetic popularity model** (`synthetic_popularity()` in `src/python/popheat_production.py`): a sum of Gaussian "bumps" per venue category and time of day (e.g. cafés peak at 9am, bars peak past midnight), with a weekend boost and small random noise. It is not real foot-traffic data, and the code says so.

This is disclosed here and in the accompanying article so nobody mistakes the demo for a real crowd-sensing product.

## Architecture

```
data/porto_venues.json (1,479 real OSM venues)
        │
        ▼
┌─────────────────────┐   batch of ~150 venues/tick, synthetic popularity computed
│  OverpassInAdapter   │   (InboundAdapter)
└──────────┬───────────┘
           │ business_host_process_input(readings)
           ▼
┌─────────────────────┐   wraps the batch as one VenueBatch message
│  VenueIngestService  │   (BusinessService)
└──────────┬───────────┘
           │ SendRequestSync — ONE message for the whole batch
           ▼
┌─────────────────────┐   calls the PopHeat.Rule.HeatLevel IRIS Business Rule
│ HeatClassifierProcess│   per venue (category-aware thresholds)
└──────────┬───────────┘   (BusinessProcess)
           │ SendRequestSync — classified batch
           ▼
┌─────────────────────┐   persists each venue directly to SQL (PopHeat.VenueReading)
│ HeatPersistOperation │   + writes a PopHeat.BatchMetric telemetry row
└──────────┬───────────┘   (BusinessOperation)
           ▼
   PopHeat.VenueReading (IRIS SQL table)
           │
           ▼
   Flask/WSGI dashboard (src/python/webapp/app.py)
   — reads the table in-process via `iris.sql.exec()`, no network hop —
   served directly by IRIS at /popheat/
```

**Why a whole batch travels as one message** instead of one message per venue: an earlier version routed one PyProd message per venue through all three hosts. At ~1,500 venues that meant ~3,000 synchronous inter-host round trips per refresh cycle — a full refresh took over an hour. Batching the venues into a single `VenueBatch` message (and persisting rows directly via `iris.cls(...)._New()/._Save()` instead of one more messaging hop per row) brought a full refresh down to well under a minute.

## Contest scorecard (PyProd track)

| Requirement | Points | Status |
|---|---|---|
| Base PyProd interoperability project | 5 | ✅ |
| At least 3 hosts (Service + Process + Operation) | +1 | ✅ |
| Adapter in a host (`OverpassInAdapter`) | +1 | ✅ |
| Business Rules (`PopHeat.Rule.HeatLevel`) | +2 | ✅ |
| WSGI web application (Flask dashboard) | +3 | ✅ |
| Monitoring/telemetry (`PopHeat.BatchMetric` + `/api/telemetry`) | +2 | ✅ |
| IntegratedML | +3 | not attempted |

## Prerequisites

- Docker + Docker Compose
- ~2 GB free RAM for the IRIS container
- Internet access on first data refresh only (`data/fetch_venues.py`, already run — `data/porto_venues.json` is committed)

## Quick start

```bash
docker compose up -d
bash iris/setup.sh
```

`setup.sh` is idempotent and does everything by itself: sets the `_SYSTEM` password, enables `%Service_CallIn`, creates the `POPHEAT` interoperability namespace, flips ENSLIB to read/write (it ships read-only on the community image), registers the WSGI dashboard and the namespace's Management Portal web application, compiles the Business Rule, installs `intersystems_pyprod` + `flask` into IRIS's embedded Python, generates+loads the PyProd production classes, grants the dashboard read access, and starts the production.

Once it finishes:

| What | URL | Credentials |
|---|---|---|
| **Dashboard (heatmap)** | http://localhost:52773/popheat/ | — (public) |
| Management Portal (this namespace) | http://localhost:52773/csp/popheat/UtilHome.csp | `_SYSTEM` / `PopHeat2026!` |
| Production diagram | http://localhost:52773/csp/popheat/EnsPortal.ProductionConfig.zen?PRODUCTION=PopHeat.PopHeatProduction | same |

> These are local development credentials for a container that isn't exposed beyond `localhost` by default. Change them before deploying anywhere reachable.

## Project structure

```
docker-compose.yml           IRIS Community Edition container
iris/setup.sh, setup.txt     One-shot idempotent environment setup
src/python/popheat_production.py   The PyProd production (Service/Process/Operation/Adapter)
src/python/webapp/app.py     Flask/WSGI dashboard, hosted directly by IRIS
src/objectscript/            The IRIS Business Rule + its context class
data/porto_venues.json       1,479 real Porto venues (OpenStreetMap)
data/fetch_venues.py         Script used to (re)generate that dataset for any bounding box
```

## Data & licensing

- Code: MIT (see `LICENSE`).
- `data/porto_venues.json` is derived from **OpenStreetMap** data, © OpenStreetMap contributors, available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). The dashboard's map tiles also carry the OSM attribution in the UI, as required.
- Popularity scores in that dataset are synthetic (see above) — they are not derived from any real observed data.

## Changing the city

Edit `BBOX` in `data/fetch_venues.py` to any bounding box, rerun it to regenerate `data/porto_venues.json`, and update the map's initial view in `src/python/webapp/app.py` (`map.setView([lat, lon], zoom)`).

## Author

Jean Cruz ([Developer Community profile link here](#)) — built with AI-assisted development (Claude Code) as part of the InterSystems PT AI Programming Contest 2026. See the accompanying article on the Portuguese Developer Community for the full methodology, prompts, and AI-tool usage writeup.
