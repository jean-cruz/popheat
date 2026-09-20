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

}
