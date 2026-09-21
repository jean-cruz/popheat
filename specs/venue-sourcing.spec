SPEC: Venue Sourcing

PURPOSE
  Define which real-world places are eligible to appear as venues, and how
  the venue catalog is built.

RULES

  R1. Venue eligibility
      A place is included in the venue catalog only if its OpenStreetMap
      `amenity` tag is one of: bar, pub, restaurant, cafe, fast_food,
      nightclub.

  R2. Required fields
      A place is discarded if it is missing a name, latitude, longitude, or
      amenity tag. Venues without a name cannot be shown meaningfully on the
      dashboard or in popups.

  R3. Geographic scope
      Venues are collected only within a configured bounding box (one city
      area at a time). Changing the area of coverage means changing this
      bounding box and regenerating the catalog; it does not require any
      other code change.

  R4. Deduplication
      A venue is considered a duplicate, and dropped, if another entry
      already shares the same name and the same coordinates rounded to 5
      decimal places (~1.1m precision).

  R5. Venue identity
      Each venue keeps a stable identifier derived from its source record,
      so repeated observations of the same physical place can be linked
      together over time.

  R6. Catalog refresh is manual
      The venue catalog (identity, name, category, location) is a static
      snapshot regenerated on demand, not on every cycle. Only crowdedness
      (see popularity-model.spec) is recomputed continuously.
