Class PopHeat.Reading Extends %Persistent
{

/// OSM-derived venue identifier, e.g. "node/1223740137" (INGE-06).
Property VenueId As %String(MAXLEN = 255);

/// Venue display name at the time of this reading (INGE-06).
Property VenueName As %String(MAXLEN = 255);

/// OSM amenity category: bar, pub, restaurant, cafe, fast_food, nightclub,
/// or another value falling back to the generic popularity curve (INGE-06,
/// POPU-02).
Property Category As %String(MAXLEN = 100);

Property Latitude As %Double;

Property Longitude As %Double;

/// Synthetic popularity score in [0.02, 0.98], 3 decimal places (POPU-01).
/// Never backed by a real "how busy is this place" source (POPU-06).
Property Popularity As %Numeric(SCALE = 3);

/// One of BAIXO, MEDIO, ALTO, CRITICO (HEAT-01, HEAT-02).
Property HeatLevel As %String(MAXLEN = 20);

/// Timestamp this reading was observed at, Europe/Lisbon local time (D-02).
Property ObservedAt As %TimeStamp;

/// Every persisted reading is a brand-new row; PopHeat.Reading is
/// insert-only (INGE-07, D-07) -- there is no separate "latest reading"
/// table. Do not add UPDATE/DELETE logic against this class.
Index ObservedAtIdx On ObservedAt;

Index VenueIdx On VenueId;

/// The single latest reading per venue (DASH-01, D-04) -- the one source of
/// truth for both the map (/venues) and the heat-level counts (/venues and
/// /counts must never drift apart, per D-04). ObservedAt DESC picks the
/// newest reading for each VenueId; ID DESC is a deterministic tiebreak for
/// two readings sharing the exact same ObservedAt, since Reading is
/// insert-only and ID increases with insert order.
Query LatestPerVenue() As %SQLQuery
{
SELECT VenueId, VenueName, Category, Latitude, Longitude, Popularity, HeatLevel, ObservedAt
FROM (
  SELECT VenueId, VenueName, Category, Latitude, Longitude, Popularity, HeatLevel, ObservedAt,
         ROW_NUMBER() OVER (PARTITION BY VenueId ORDER BY ObservedAt DESC, ID DESC) AS RowNum
  FROM PopHeat.Reading
) WHERE RowNum = 1
ORDER BY VenueId ASC
}

}
