SPEC: Ingestion Pipeline

PURPOSE
  Define how venues move from the static catalog through scoring,
  classification, and persistence, and the batching rules that keep this
  affordable at the full catalog size.

RULES

  R1. Batch size and cadence
      Venues are processed in batches of 150 at a time, with 3 seconds
      between the start of one batch and the next.

  R2. Full-catalog cycling
      Ingestion walks the venue catalog from start to end in fixed-size
      batches; when it reaches the end, it wraps back to the beginning
      and continues. Every venue is revisited on a regular cycle, not just
      once.

  R3. Batch atomicity end-to-end
      A batch of venues is scored, classified, and persisted as one unit
      that travels together through the pipeline. Venues are never split
      across pipeline stages mid-batch, and a batch is not partially
      classified with a different batch's readings.

  R4. Failure isolation
      A failure while producing or handling one batch is recorded as an
      error for that batch; it does not stop the next scheduled batch from
      being processed.

  R5. Every reading carries its full context downstream
      Every reading that reaches persistence includes: venue identity,
      name, category, coordinates, computed popularity, assigned heat
      level, and the timestamp it was observed at. No stage is allowed to
      drop these fields before persistence.

  R6. One reading is a new row, not an update
      Persisting a reading always inserts a new observation; it never
      overwrites a venue's previous reading. Historical readings for a
      venue are retained.
