SPEC: Popularity Model

PURPOSE
  Define how a venue's current crowdedness score is derived, in the absence
  of any real, ToS-compliant, free live "how busy is this place" data
  source. The score is a documented estimate, not a measurement.

RULES

  R1. Score range
      Popularity is always a number between 0.02 and 0.98 (never fully
      empty, never fully saturated), rounded to 3 decimal places.

  R2. Category shapes the daily curve
      Each venue category follows its own expected busy pattern across the
      day, expressed as one or more peak hours with a width and a height:
        - cafe: peaks around 9h (breakfast) and 15h (afternoon)
        - restaurant: peaks around 13h (lunch) and 20h (dinner)
        - fast_food: peaks around 13h and 20h, lower intensity than restaurant
        - bar: peaks around 22h and 1h (late night, wraps past midnight)
        - pub: peaks around 21h and 0h
        - nightclub: peaks around 1h and 3h (after-midnight only)
        - any other category: falls back to a generic lunch (13h) /
          evening (20h) pattern

  R3. Time distance wraps at midnight
      When measuring how close the current time is to a peak hour, the
      distance between 23h and 1h is treated as 2 hours, not 22 — the day
      is circular.

  R4. Weekend boost
      From Friday through Sunday, the computed score is boosted by 20%
      before being clamped to the valid range.

  R5. Controlled randomness
      A small random adjustment (between -0.06 and +0.06) is applied to
      every reading so that repeated observations of the same venue at the
      same hour are not identical.

  R6. Recomputed every cycle
      Popularity is not stored/reused between cycles — it is recalculated
      fresh for every venue on every ingestion tick, using the current
      timestamp.
