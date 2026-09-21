SPEC: Dashboard & API

PURPOSE
  Define what the live dashboard shows to a viewer and the rules behind
  each of its data endpoints.

RULES

  R1. Latest reading per venue only
      Venue-facing views (map, list, counts) always show each venue's most
      recent reading. Older readings for the same venue are historical
      data, not shown as current state.

  R2. Heat map reflects all venues
      Every venue with at least one reading contributes a point to the heat
      map, weighted by its current popularity score (a minimum visible
      weight is applied so low-popularity venues are not invisible).

  R3. Only high-concern venues get individual markers
      Discrete, clickable markers are shown only for venues currently
      classified ALTO or CRITICO. BAIXO and MEDIO venues appear on the heat
      layer but do not get their own marker — this keeps the map readable
      at a glance rather than cluttered with every venue.

  R4. Marker prominence follows severity
      A CRITICO marker is rendered larger than an ALTO marker, so the more
      urgent case is visually more prominent even before reading the
      popup.

  R5. Aggregate counts must match displayed data
      The count of venues per heat level shown to the viewer is always
      computed from the same "latest reading per venue" rule as R1 — it
      never counts historical readings, which would inflate totals.

  R6. Production status is informational, not gating
      The dashboard reports whether the underlying ingestion pipeline is
      currently running, but continues to serve the last known data
      regardless of that status rather than failing or blanking out.

  R7. Client refresh cadence
      The dashboard re-fetches venues, counts, and telemetry every 10
      seconds. A fetch failure is shown to the viewer as a visible error
      state rather than silently leaving stale data displayed as if it
      were current.
