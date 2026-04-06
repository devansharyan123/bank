from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, Enum as SAEnum, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.enums import UserRole

if TYPE_CHECKING:
    from models.account import BankAccount
    from models.loan import Loan


class User(Base):
    """
    Represents a bank customer or admin.

    A user must complete KYC (Aadhaar + PAN) before opening an account.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.customer)

    # KYC fields — set when the user submits Aadhaar + PAN
    kyc_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    aadhaar_number: Mapped[str | None] = mapped_column(String(14), nullable=True)  # XXXX-XXXX-XXXX
    pan_number: Mapped[str | None] = mapped_column(String(10), nullable=True)       # ABCDE1234F

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # One user can have many accounts and loans
    accounts: Mapped[list[BankAccount]] = relationship(
        "BankAccount", back_populates="owner", cascade="all, delete-orphan"
    )
    loans: Mapped[list[Loan]] = relationship(
        "Loan", foreign_keys="[Loan.user_id]", back_populates="borrower", cascade="all, delete-orphan"
    )
