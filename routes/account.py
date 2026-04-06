from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.account import BankAccount
from models.user import User
from models.enums import AccountType
from schemas.account import CreateAccountRequest, AccountResponse, InterestResponse
from utils.security import get_current_user
from utils.logger import logger

router = APIRouter(tags=["Accounts"])

# Minimum opening balance per account type
MINIMUM_BALANCE = {
    AccountType.savings: Decimal("500.00"),
    AccountType.current: Decimal("1000.00"),
}

# Annual interest rate per account type
INTEREST_RATES = {
    AccountType.savings: Decimal("4.00"),
    AccountType.current: Decimal("2.00"),
}


def generate_account_number(db: Session) -> str:
    """Generate a sequential account number like ACC1001, ACC1002, ..."""
    count = db.query(BankAccount).count()
    return f"ACC{1001 + count}"


def calculate_monthly_interest(balance: Decimal, annual_rate: Decimal) -> Decimal:
    """Monthly interest = (balance × annual_rate) / (12 × 100)"""
    return (balance * annual_rate / (Decimal("12") * Decimal("100"))).quantize(Decimal("0.01"))


@router.post("/", response_model=AccountResponse, status_code=201)
def open_account(
    data: CreateAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Open a new bank account.

    Steps:
    1. Check the user has completed KYC
    2. Verify the opening deposit meets the minimum balance
    3. Create the account
    """
    if not current_user.kyc_verified:
        raise HTTPException(status_code=403, detail="Complete KYC verification before opening an account.")

    required_min = MINIMUM_BALANCE[data.account_type]
    if data.initial_deposit < required_min:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum opening deposit for {data.account_type} account is ₹{required_min}.",
        )

    account = BankAccount(
        account_number=generate_account_number(db),
        user_id=current_user.id,
        account_type=data.account_type,
        balance=data.initial_deposit,
        minimum_balance=required_min,
        interest_rate=INTEREST_RATES[data.account_type],
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    logger.info(f"Account {account.account_number} opened for user {current_user.email}")
    return account


@router.get("/", response_model=list[AccountResponse])
def list_my_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all accounts belonging to the logged-in user."""
    return db.query(BankAccount).filter(BankAccount.user_id == current_user.id).all()


@router.get("/{account_number}", response_model=AccountResponse)
def get_account(
    account_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get details of a specific account by its account number."""
    account = db.query(BankAccount).filter(BankAccount.account_number == account_number).first()
    if account is None:
        raise HTTPException(status_code=404, detail=f"Account '{account_number}' not found.")
    return account


@router.post("/{account_number}/apply-interest", response_model=InterestResponse)
def apply_monthly_interest(
    account_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Add one month's interest to an account balance.

    Interest = (balance × annual_rate) / (12 × 100)
    """
    account = db.query(BankAccount).filter(BankAccount.account_number == account_number).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found.")
    if account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only apply interest to your own accounts.")

    interest_earned = calculate_monthly_interest(account.balance, account.interest_rate)
    account.balance += interest_earned
    db.commit()
    db.refresh(account)

    return InterestResponse(
        account_number=account.account_number,
        interest_earned=interest_earned,
        new_balance=account.balance,
    )
