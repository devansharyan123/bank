from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class LoanApplyRequest(BaseModel):
    principal: Decimal = Field(gt=0, description="Loan amount in ₹")
    annual_rate: Decimal = Field(gt=0, le=50, description="Annual interest rate in %")
    tenure_months: int = Field(gt=0, le=360, description="Loan duration in months")


class LoanResponse(BaseModel):
    id: int
    user_id: int
    principal: Decimal
    annual_rate: Decimal
    tenure_months: int
    emi_amount: Decimal
    status: str
    rejection_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class EMIBreakdownResponse(BaseModel):
    """Detailed EMI calculation — returned before formally applying for a loan."""
    principal: Decimal
    annual_rate: Decimal
    tenure_months: int
    monthly_emi: Decimal
    total_payment: Decimal
    total_interest: Decimal


class LoanActionRequest(BaseModel):
    """Admin sends this when approving or rejecting a loan."""
    rejection_reason: str | None = None
