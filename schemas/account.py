from decimal import Decimal
from pydantic import BaseModel, Field
from models.enums import AccountType


class CreateAccountRequest(BaseModel):
    account_type: AccountType
    initial_deposit: Decimal = Field(ge=0, description="Opening deposit in ₹")


class AccountResponse(BaseModel):
    id: int
    account_number: str
    account_type: str
    balance: Decimal
    minimum_balance: Decimal
    interest_rate: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class InterestResponse(BaseModel):
    account_number: str
    interest_earned: Decimal
    new_balance: Decimal
