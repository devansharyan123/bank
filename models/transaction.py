from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.enums import TransactionType, TransactionStatus

if TYPE_CHECKING:
    from models.account import BankAccount


class Transaction(Base):
    """
    Records every money movement — deposit, withdrawal, or transfer.

    Failed transactions are also saved so there is a complete audit trail,
    including rollback demos when simulate_failure=True is used.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reference_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # For deposits: from_account_id is None (money comes from outside)
    # For withdrawals: to_account_id is None (money goes outside)
    # For transfers: both are filled
    from_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)
    to_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True)

    transaction_type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    status: Mapped[TransactionStatus] = mapped_column(SAEnum(TransactionStatus), default=TransactionStatus.pending)

    # Fraud detection flags
    is_flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flagged_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Filled when a transaction fails (including simulate_failure rollback demo)
    failure_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    from_account: Mapped[BankAccount | None] = relationship(
        "BankAccount", foreign_keys=[from_account_id], back_populates="sent_transactions"
    )
    to_account: Mapped[BankAccount | None] = relationship(
        "BankAccount", foreign_keys=[to_account_id], back_populates="received_transactions"
    )
