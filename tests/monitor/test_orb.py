import csv
import datetime as dt
from pathlib import Path

from src.monitor import ORBEvent, ORBMonitor, ORBSettings


def test_orb_monitor_emits_breakouts(tmp_path: Path):
    csv_path = tmp_path / "prices.csv"
    rows = [
        {"timestamp": "2024-01-01T09:00:00", "price": "100"},
        {"timestamp": "2024-01-01T09:05:00", "price": "101"},
        {"timestamp": "2024-01-01T09:15:00", "price": "102"},
        {"timestamp": "2024-01-01T09:20:00", "price": "103"},
        {"timestamp": "2024-01-01T09:25:00", "price": "99"},
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "price"])
        writer.writeheader()
        writer.writerows(rows)

    captured: list[ORBEvent] = []

    def dispatch(event: ORBEvent) -> None:
        captured.append(event)

    monitor = ORBMonitor(ORBSettings(), dispatch)
    events = monitor.run_csv(csv_path, "005930")
    assert captured == events
    assert events[0].direction == "long"
    assert len(events) == 2