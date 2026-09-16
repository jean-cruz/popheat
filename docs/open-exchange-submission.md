# Open Exchange submission — copy/paste content

Log in at https://openexchange.intersystems.com/ and click **"Submit application"** in the top nav. Paste the GitHub URL first — it auto-fills name/description/license from the repo, then adjust with the text below.

## Repository URL
```
https://github.com/jean-cruz/popheat
```

## Application name
```
PopHeat
```

## Short description (catalog card, ~150 chars)
```
Live crowdedness heatmap for São Paulo built as a pure-Python IRIS Interoperability Production (PyProd) with Business Rules and a WSGI dashboard.
```

## Full description
```
PopHeat ingests ~650 real venues (bars, restaurants, cafés, pubs, nightclubs) in São Paulo from OpenStreetMap, scores how crowded each one likely is right now with a transparent synthetic model (no free real-time crowd API exists — see README for why), classifies that score through a real InterSystems IRIS Business Rule, persists it to SQL, and renders it as a live heatmap on a Flask dashboard hosted directly by IRIS via WSGI.

Built entirely as a pure-Python IRIS interoperability production using PyProd (Service → Process → Operation, with an Inbound Adapter), for the InterSystems Portuguese Community AI Programming Contest 2026.

One command reproduces the whole environment: docker compose up -d && bash iris/setup.sh.
```

## Category
```
Interoperability
```
(alternate if that option isn't available: "Solution" or "IoT/Analytics")

## InterSystems technology tags
```
InterSystems IRIS
Embedded Python
Interoperability
Business Rules
```

## Other tags
```
heatmap, pyprod, flask, wsgi, openstreetmap, dashboard, ai-programming-contest
```

## License URL
```
https://github.com/jean-cruz/popheat/blob/main/LICENSE
```

## About / Demo URL
Leave blank, or link to the Developer Community article once published (see docs/artigo-pt.md).

## AI/ML checkbox
Check it if offered — this is an AI-programming-contest entry, and the whole build process used AI-assisted development (documented in the DC article).

## Screenshot
Upload `docs/images/dashboard.png` (already embedded in the README too).

---

### Checklist before submitting
- [ ] Repo `jean-cruz/popheat` set to **public**
- [ ] `git push` done (local commits are ahead of `origin/main` as of the last check)
- [ ] README's "Author" section has your real Developer Community profile link (currently a placeholder)
- [ ] (Optional) Publish the DC article first so you can paste its URL into the Open Exchange listing
