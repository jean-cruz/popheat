/// Read-only REST layer over Phase 2's persisted PopHeat.Reading and
/// PopHeat.BatchTelemetry data (DASH-01, DASH-05, DASH-06). Every route is
/// unauthenticated (D-06) and every SQL statement is a fixed, parameterless
/// SELECT -- no request input is ever concatenated into SQL text (T-03-01,
/// T-03-05). This class never writes to PopHeat.Reading or
/// PopHeat.BatchTelemetry.
Class PopHeat.API Extends %CSP.REST
{

XData UrlMap
{
<Routes>
<Route Url="/venues" Method="GET" Call="Venues"/>
<Route Url="/counts" Method="GET" Call="Counts"/>
<Route Url="/telemetry" Method="GET" Call="Telemetry"/>
<Route Url="/status" Method="GET" Call="Status"/>
</Routes>
}

/// Latest reading per venue (DASH-01), backed by PopHeat.Reading:LatestPerVenue
/// (D-04 single source of truth). Returns a JSON array, empty when zero
/// readings exist yet -- never an error for the legitimate empty-catalog case.
ClassMethod Venues() As %Status
{
	Try {
		Set %response.ContentType = "application/json"
		Set result = ##class(%ResultSet).%New("PopHeat.Reading:LatestPerVenue")
		Do result.Execute()
		Set venues = []
		While result.Next() {
			Set venue = {
				"venueId": (result.Get("VenueId")),
				"venueName": (result.Get("VenueName")),
				"category": (result.Get("Category")),
				"lat": (result.Get("Latitude")),
				"lon": (result.Get("Longitude")),
				"popularity": (result.Get("Popularity")),
				"heatLevel": (result.Get("HeatLevel")),
				"observedAt": (result.Get("ObservedAt"))
			}
			Do venues.%Push(venue)
		}
		Write venues.%ToJSON()
	} Catch ex {
		Set %response.Status = "500 Internal Server Error"
		Set errorObj = {"error": "query failed"}
		Write errorObj.%ToJSON()
	}
	Quit $$$OK
}

/// Venue count per heat level (DASH-05), backed by
/// PopHeat.Reading:CountsByHeatLevel -- the same latest-reading-per-venue
/// definition /venues uses (D-04). All four keys are always present, 0 for a
/// level currently held by no venue, so the counts panel renders a fixed
/// four rows rather than a variable number.
ClassMethod Counts() As %Status
{
	Try {
		Set %response.ContentType = "application/json"
		Set counts = {"BAIXO": 0, "MEDIO": 0, "ALTO": 0, "CRITICO": 0}
		Set result = ##class(%ResultSet).%New("PopHeat.Reading:CountsByHeatLevel")
		Do result.Execute()
		While result.Next() {
			Set level = result.Get("HeatLevel")
			// Only the four known levels are emitted -- an unexpected value
			// must not silently add a fifth key to the documented shape.
			If counts.%IsDefined(level) {
				Do counts.%Set(level, +result.Get("VenueCount"), "number")
			}
		}
		Write counts.%ToJSON()
	} Catch ex {
		Set %response.Status = "500 Internal Server Error"
		Set errorObj = {"error": "query failed"}
		Write errorObj.%ToJSON()
	}
	Quit $$$OK
}

/// The most recent ingestion batches (TELE-05), newest first, capped at 20
/// rows by PopHeat.BatchTelemetry:RecentBatches itself. An empty telemetry
/// table is the legitimate [] case, never an error.
ClassMethod Telemetry() As %Status
{
	Try {
		Set %response.ContentType = "application/json"
		Set result = ##class(%ResultSet).%New("PopHeat.BatchTelemetry:RecentBatches")
		Do result.Execute()
		Set batches = []
		While result.Next() {
			Set batch = {
				"readingCount": (result.Get("ReadingCount")),
				"elapsedSeconds": (result.Get("ElapsedSeconds")),
				"throughput": (result.Get("Throughput")),
				"recordedAt": (result.Get("RecordedAt"))
			}
			Do batches.%Push(batch)
		}
		Write batches.%ToJSON()
	} Catch ex {
		Set %response.Status = "500 Internal Server Error"
		Set errorObj = {"error": "query failed"}
		Write errorObj.%ToJSON()
	}
	Quit $$$OK
}

/// Whether the ingestion production is currently running (DASH-06, D-06).
/// Informational only and deliberately un-failable: the production check runs
/// in its own Try/Catch and any exception degrades to {"running": false}
/// rather than surfacing an IRIS %Status string or stack trace to a public
/// client (T-03-02). This route always answers HTTP 200, and its outcome is
/// independent of /venues, /counts and /telemetry.
ClassMethod Status() As %Status
{
	Set running = 0
	Try {
		Set prodName = ""
		Set running = ''##class(Ens.Director).IsProductionRunning(.prodName)
		If running, prodName '= "", prodName '= "PopHeat.Production" {
			Set running = 0
		}
	} Catch ex {
		Set running = 0
	}
	Set %response.ContentType = "application/json"
	Set payload = {}
	Do payload.%Set("running", running, "boolean")
	Write payload.%ToJSON()
	Quit $$$OK
}

}
