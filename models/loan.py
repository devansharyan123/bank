from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import String, Enum as SAEnum, DateTime, Numeric, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base
from models.enums import LoanStatus

if TYPE_CHECKING:
    from models.user import User


class Loan(Base):
    """
    Represents a loan application made by a customer.

    The EMI is calculated and stored when the loan is applied.
    An admin must approve or reject it.
    """
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    principal: Mapped[Decimal] = mapped_column(Numeric(15, 2))
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2))   # e.g., 10.5 = 10.5%
    tenure_months: Mapped[int] = mapped_column(Integer)

    # EMI = P * r * (1+r)^n / ((1+r)^n - 1)  — calculated at application time
    emi_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2))

    status: Mapped[LoanStatus] = mapped_column(SAEnum(LoanStatus), default=LoanStatus.pending)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    borrower: Mapped[User] = relationship("User", foreign_keys=[user_id], back_populates="loans")
    approver: Mapped[User | None] = relationship("User", foreign_keys=[approved_by])
