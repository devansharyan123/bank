from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, Field


class DepositRequest(BaseModel):
    account_number: str
    amount: Decimal = Field(gt=0, description="Amount to deposit in ₹")


class WithdrawRequest(BaseModel):
    account_number: str
    amount: Decimal = Field(gt=0, description="Amount to withdraw in ₹")


class TransferRequest(BaseModel):
    from_account_number: str
    to_account_number: str
    amount: Decimal = Field(gt=0, description="Amount to transfer in ₹")
    simulate_failure: bool = Field(
        default=False,
        description="Set true to demo ACID rollback — money returns to sender automatically."
    )


class TransactionResponse(BaseModel):
    id: int
    reference_id: str
    transaction_type: str
    amount: Decimal
    status: str
    is_flagged: bool
    flagged_reason: str | None
    failure_reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
