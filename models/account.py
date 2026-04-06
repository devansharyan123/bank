from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, Numeric, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.enums import AccountType

if TYPE_CHECKING:
    from models.user import User
    from models.transaction import Transaction


class BankAccount(Base):
    """
    Represents a single bank account belonging to a user.

    Balance is stored as Decimal (not float) to avoid rounding errors with money.
    """
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    account_type: Mapped[AccountType] = mapped_column(SAEnum(AccountType))

    # Decimal for exact money values — never use float for currency
    balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"))
    minimum_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("500.00"))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("4.00"))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    owner: Mapped[User] = relationship("User", back_populates="accounts")
    sent_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", foreign_keys="Transaction.from_account_id", back_populates="from_account"
    )
    received_transactions: Mapped[list[Transaction]] = relationship(
        "Transaction", foreign_keys="Transaction.to_account_id", back_populates="to_account"
    )
