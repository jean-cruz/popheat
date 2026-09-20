Class PopHeat.BatchTelemetry Extends %Persistent
{

/// Number of readings persisted in this batch (TELE-02).
Property ReadingCount As %Integer;

/// Wall-clock seconds spent persisting this batch (TELE-02).
Property ElapsedSeconds As %Numeric(SCALE = 3);

/// ReadingCount / ElapsedSeconds, or 0 when ElapsedSeconds is 0 rather than
/// divided-by-zero/omitted (TELE-02, TELE-03).
Property Throughput As %Numeric(SCALE = 3);

/// When this telemetry record was recorded, Europe/Lisbon local time (D-02).
Property RecordedAt As %TimeStamp;

/// One row per persisted batch (TELE-01); never updated after insert.
Index RecordedAtIdx On RecordedAt;

/// Operational visibility into the most recent batches only (TELE-05):
/// the latest 20 telemetry rows, newest first -- never the full
/// historical log, so throughput reporting reflects current behavior.
Query RecentBatches() As %SQLQuery(CONTAINID = 1)
{
SELECT TOP 20 ID, ReadingCount, ElapsedSeconds, Throughput, RecordedAt
FROM PopHeat.BatchTelemetry
ORDER BY RecordedAt DESC
}

}
