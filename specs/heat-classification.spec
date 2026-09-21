SPEC: Heat Level Classification

PURPOSE
  Define how a numeric popularity score is turned into one of four
  business-facing crowdedness labels, and why nightlife venues are judged
  on a different scale than daytime venues.

LABELS
  BAIXO (low), MEDIO (medium), ALTO (high), CRITICO (critical) — in
  increasing order of crowdedness. Every reading gets exactly one label.

RULES

  R1. Nightlife gets its own thresholds
      Venues whose category is bar, pub, or nightclub are naturally busier
      late at night than daytime venues ever get. They are classified on a
      lower popularity scale so that a "normal busy night" for a bar does
      not read as CRITICO the way it would for a cafe:
        - popularity >= 0.60  -> CRITICO
        - popularity >= 0.40  -> ALTO
        - popularity >= 0.20  -> MEDIO
        - otherwise            -> BAIXO

  R2. All other categories use daytime thresholds
      - popularity >= 0.75  -> CRITICO
      - popularity >= 0.50  -> ALTO
      - popularity >= 0.25  -> MEDIO
      - otherwise            -> BAIXO

  R3. Evaluation order
      Rules are evaluated from the highest threshold down to the lowest,
      within a venue's applicable rule set (nightlife or daytime); the
      first matching rule wins.

  R4. Thresholds are configuration, not code
      The threshold values above are the current defaults and are expected
      to be retuned independently of the rest of the system (e.g. by a
      business analyst), without requiring a code change or redeploy of the
      ingestion/persistence pipeline.

  R5. Unclassifiable readings default to BAIXO
      If classification cannot produce a label for a reading, the reading
      is treated as BAIXO rather than left unlabeled or rejected.
