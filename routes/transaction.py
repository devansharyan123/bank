from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.transaction import DepositRequest, WithdrawRequest, TransferRequest, TransactionResponse
from services.payment_service import PaymentService
from utils.security import get_current_user

router = APIRouter(tags=["Transactions"])
payment_service = PaymentService()


@router.post("/deposit", response_model=TransactionResponse)
def deposit(
    data: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deposit money into one of your accounts."""
    return payment_service.deposit(db, current_user, data)


@router.post("/withdraw", response_model=TransactionResponse)
def withdraw(
    data: WithdrawRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Withdraw money from one of your accounts."""
    return payment_service.withdraw(db, current_user, data)


@router.post("/transfer", response_model=TransactionResponse)
def transfer(
    data: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Transfer money to another account.

    Pass simulate_failure=true to see ACID rollback in action:
    money leaves the sender's account in memory, then the transaction fails,
    and SQLAlchemy automatically restores the sender's balance.
    """
    return payment_service.transfer(db, current_user, data)


@router.get("/history/{account_number}", response_model=list[TransactionResponse])
def get_history(
    account_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the full transaction history for one of your accounts."""
    return payment_service.get_history(db, account_number, current_user)
