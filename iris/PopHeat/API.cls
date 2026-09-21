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

}
