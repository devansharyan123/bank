"""
fraud_detection.py — Sliding window algorithm for detecting suspicious transactions.

Algorithm explanation:
  A "sliding window" is a fixed-size time range that moves forward as time passes.
  At any moment, we only look at transactions that happened within the last N minutes.
  Transactions older than the window automatically fall out of consideration.

  Time complexity: O(n) where n = number of recent transactions checked.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy.orm import Session
from models.account import BankAccount
from models.transaction import Transaction
from database import get_settings

settings = get_settings()


def count_transactions_in_window(transactions: list, window_minutes: int) -> int:
    """
    Count how many transactions happened within the last N minutes.

    This is the core of the sliding window algorithm.
    """
    window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)

    recent_count = sum(
        1 for tx in transactions
        if tx.created_at >= window_start
    )
    return recent_count


def check_for_fraud(
    amount: Decimal,
    recent_transactions: list,
) -> tuple[bool, str | None]:
    """
    Run all fraud checks on a transaction before it is processed.

    Returns:
        (is_suspicious, reason) — if not suspicious, reason is None.

    Checks performed:
        1. Is the amount unusually large?
        2. Is this account sending money too rapidly?
    """
    large_amount_threshold = Decimal(str(settings.fraud_large_amount))

    # Check 1: Large amount detection
    if amount >= large_amount_threshold:
        return True, f"Large transfer of ₹{amount} detected (threshold: ₹{large_amount_threshold})"

    # Check 2: Rapid transactions (sliding window)
    recent_count = count_transactions_in_window(
        recent_transactions,
        settings.fraud_rapid_tx_window_minutes,
    )
    if recent_count >= settings.fraud_rapid_tx_count:
        return True, (
            f"Rapid transactions: {recent_count} transfers in the last "
            f"{settings.fraud_rapid_tx_window_minutes} minutes"
        )

    return False, None


def run_fraud_check(db: Session, account: BankAccount, amount: Decimal) -> tuple[bool, str | None]:
    """
    Load recent transactions for an account and run all fraud checks.

    Used by payment_service before processing any transfer.
    """
    recent_transactions = (
        db.query(Transaction)
        .filter(Transaction.from_account_id == account.id)
        .order_by(Transaction.created_at.desc())
        .limit(50)
        .all()
    )

    return check_for_fraud(amount, recent_transactions)
