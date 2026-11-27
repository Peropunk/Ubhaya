"""P2.2 source time conversion and uncertainty."""

import pytest

from app.timeengine import event_range


@pytest.mark.parametrize(
    ("artifact_type", "original_time", "original_tz", "expected"),
    [
        ("door_log", "2025-12-03 21:52:07", "Asia/Kolkata",
         ("2025-12-03T21:51:07+05:30", "2025-12-03T21:53:07+05:30")),
        ("bank_upi", "2025-12-03T18:30:00Z", "UTC",
         ("2025-12-03T23:59:00+05:30", "2025-12-04T00:01:00+05:30")),
        ("chat_export", "2025-12-03 22:07", "Asia/Kolkata",
         ("2025-12-03T22:06:00+05:30", "2025-12-03T22:08:00+05:30")),
        ("cctv_still", "2025-12-03 22:05:40", "Asia/Kolkata",
         ("2025-12-03T21:55:40+05:30", "2025-12-03T22:15:40+05:30")),
    ],
)
def test_event_range(artifact_type, original_time, original_tz, expected):
    assert event_range(artifact_type, original_time, original_tz) == expected


def test_timestamp_requires_time_of_day():
    with pytest.raises(ValueError, match="ISO date and time"):
        event_range("door_log", "2025-12-03", "Asia/Kolkata")


@pytest.mark.parametrize(("clock", "center"), [
    ("12:00 AM", "2025-12-03T00:00"),
    ("12:00 pm", "2025-12-03T12:00"),
    ("I am sure it was 9:50", "2025-12-03T21:50"),
    ("9:50am on 4 December", "2025-12-04T09:50"),
    ("00:15", "2025-12-03T00:15"),
])
def test_claim_clock(clock, center):
    from app.timeengine.claims import claim_window
    low, high = claim_window(clock, "2025-12-03", None)
    assert (low + (high-low)/2).isoformat(timespec="minutes") == center + "+05:30"
