"""Tests for the sliding window fraud detection algorithm."""

from services.fraud_detection import count_transactions_in_window, check_for_fraud
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock


def make_fake_transaction(minutes_ago: int):
    """Create a fake transaction object with a timestamp N minutes in the past."""
    tx = MagicMock()
    tx.created_at = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return tx


def test_sliding_window_counts_only_recent():
    """Only transactions within the time window should be counted."""
    transactions = [
        make_fake_transaction(2),   # 2 minutes ago — inside window
        make_fake_transaction(5),   # 5 minutes ago — inside window
        make_fake_transaction(15),  # 15 minutes ago — OUTSIDE window of 10 minutes
    ]
    count = count_transactions_in_window(transactions, window_minutes=10)
    assert count == 2


def test_fraud_detected_large_amount():
    """A single large transfer should trigger a fraud flag."""
    is_flagged, reason = check_for_fraud(
        amount=Decimal("200000"),   # ₹2,00,000 — above ₹1,00,000 threshold
        recent_transactions=[],
    )
    assert is_flagged is True
    assert "Large transfer" in reason


def test_fraud_detected_rapid_transactions():
    """5 or more transactions in 10 minutes should trigger a fraud flag."""
    recent_txns = [make_fake_transaction(i) for i in range(1, 6)]  # 5 transactions within 1-5 mins
    is_flagged, reason = check_for_fraud(
        amount=Decimal("100"),
        recent_transactions=recent_txns,
    )
    assert is_flagged is True
    assert "Rapid" in reason


def test_no_fraud_for_normal_transaction():
    """A normal small transaction with no rapid history should not be flagged."""
    is_flagged, reason = check_for_fraud(
        amount=Decimal("500"),
        recent_transactions=[make_fake_transaction(30)],  # 1 transaction 30 mins ago
    )
    assert is_flagged is False
    assert reason is None
