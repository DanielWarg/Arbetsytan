"""
Verifiering: datum/tid-maskning ska vara deterministisk och idempotent.
Ingen rå content loggas.
"""

from text_processing import mask_datetime


def test_mask_datetime_strict_basic():
    text = "Möte 2026-01-06 13:24."
    masked, stats = mask_datetime(text, level="strict")
    assert masked == "Möte [DATUM] [TID]."
    assert stats["datetime_masked"] is True
    assert stats["datetime_mask_count"] >= 2


def test_mask_datetime_idempotent():
    text = "Möte 2026-01-06 13:24."
    masked1, _ = mask_datetime(text, level="strict")
    masked2, _ = mask_datetime(masked1, level="strict")
    assert masked1 == masked2

