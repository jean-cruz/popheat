SPEC: Telemetry

PURPOSE
  Define what operational metrics are recorded about the ingestion pipeline
  itself, separate from the venue data it produces.

RULES

  R1. One metric record per batch
      Every time a batch of readings is persisted, exactly one telemetry
      record is written alongside it, covering that batch only.

  R2. Required metric fields
      Each telemetry record captures: how many readings were in the batch,
      how long persisting the batch took (seconds), the resulting
      throughput (readings per second), and when it was recorded.

  R3. Throughput is derived, not estimated
      Throughput is computed as batch size divided by elapsed time for that
      same batch; if elapsed time is zero or unavailable, throughput is
      reported as zero rather than divided-by-zero or omitted.

  R4. Telemetry never blocks venue data
      A failure while recording telemetry must not prevent the venue
      readings themselves from being persisted.

  R5. Recent-history view
      Operational visibility is based on the most recent batches (the
      latest 20), not the full historical telemetry log, so throughput
      reporting reflects current behavior rather than long-run averages.
