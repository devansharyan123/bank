from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from utils.security import require_admin
from models.user import User
from models.account import BankAccount
from models.transaction import Transaction
from models.loan import Loan
from models.enums import TransactionType, TransactionStatus, LoanStatus

router = APIRouter(tags=["Admin"])


@router.get("/dashboard")
def get_dashboard(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin dashboard — counts and totals across the whole bank."""
    total_users        = db.query(User).count()
    total_accounts     = db.query(BankAccount).count()
    total_transactions = db.query(Transaction).count()
    total_loans        = db.query(Loan).count()
    pending_loans      = db.query(Loan).filter(Loan.status == LoanStatus.pending).count()
    flagged_txns       = db.query(Transaction).filter(Transaction.is_flagged == True).count()

    deposits    = db.query(Transaction).filter(Transaction.transaction_type == TransactionType.deposit,    Transaction.status == TransactionStatus.success).all()
    withdrawals = db.query(Transaction).filter(Transaction.transaction_type == TransactionType.withdraw,   Transaction.status == TransactionStatus.success).all()

    return {
        "total_users":          total_users,
        "total_accounts":       total_accounts,
        "total_transactions":   total_transactions,
        "total_loans":          total_loans,
        "pending_loans":        pending_loans,
        "flagged_transactions": flagged_txns,
        "total_deposits":       str(sum(t.amount for t in deposits)   or Decimal("0")),
        "total_withdrawals":    str(sum(t.amount for t in withdrawals) or Decimal("0")),
    }


@router.get("/fraud-alerts")
def get_fraud_alerts(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """All transactions flagged as suspicious."""
    flagged = db.query(Transaction).filter(Transaction.is_flagged == True).order_by(Transaction.created_at.desc()).all()
    return [
        {
            "id":                  tx.id,
            "reference_id":        tx.reference_id,
            "amount":              str(tx.amount),
            "flagged_reason":      tx.flagged_reason,
            "created_at":          tx.created_at,
            "from_account_number": tx.from_account.account_number if tx.from_account else None,
            "to_account_number":   tx.to_account.account_number   if tx.to_account   else None,
        }
        for tx in flagged
    ]


@router.get("/users")
def list_all_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """All registered users with their account counts."""
    users = db.query(User).all()
    return [
        {
            "id":            u.id,
            "name":          u.name,
            "email":         u.email,
            "role":          u.role,
            "kyc_verified":  u.kyc_verified,
            "account_count": len(u.accounts),
        }
        for u in users
    ]
