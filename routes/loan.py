from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.loan import Loan
from models.user import User
from models.enums import LoanStatus
from schemas.loan import LoanApplyRequest, LoanResponse, EMIBreakdownResponse, LoanActionRequest
from utils.security import get_current_user, require_admin
from utils.logger import logger

router = APIRouter(tags=["Loans"])


def calculate_emi(principal: Decimal, annual_rate_percent: Decimal, tenure_months: int) -> Decimal:
    """
    EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)

    Where:
        P = Principal
        r = Monthly interest rate = annual_rate / 12 / 100
        n = Number of months
    """
    if annual_rate_percent == 0:
        return (principal / Decimal(tenure_months)).quantize(Decimal("0.01"))

    monthly_rate = annual_rate_percent / Decimal("12") / Decimal("100")
    growth_factor = (1 + monthly_rate) ** tenure_months
    emi = (principal * monthly_rate * growth_factor) / (growth_factor - 1)
    return emi.quantize(Decimal("0.01"))


@router.post("/calculate-emi", response_model=EMIBreakdownResponse)
def get_emi_preview(data: LoanApplyRequest):
    """
    Calculate the EMI breakdown without applying for the loan.

    Useful to show the customer what their monthly payments would be.
    """
    monthly_emi = calculate_emi(data.principal, data.annual_rate, data.tenure_months)
    total_payment = (monthly_emi * data.tenure_months).quantize(Decimal("0.01"))
    total_interest = (total_payment - data.principal).quantize(Decimal("0.01"))

    return EMIBreakdownResponse(
        principal=data.principal,
        annual_rate=data.annual_rate,
        tenure_months=data.tenure_months,
        monthly_emi=monthly_emi,
        total_payment=total_payment,
        total_interest=total_interest,
    )


@router.post("/apply", response_model=LoanResponse, status_code=201)
def apply_for_loan(
    data: LoanApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Apply for a loan. EMI is calculated and saved automatically.

    KYC must be completed first.
    """
    if not current_user.kyc_verified:
        raise HTTPException(status_code=403, detail="Complete KYC verification before applying for a loan.")

    monthly_emi = calculate_emi(data.principal, data.annual_rate, data.tenure_months)

    loan = Loan(
        user_id=current_user.id,
        principal=data.principal,
        annual_rate=data.annual_rate,
        tenure_months=data.tenure_months,
        emi_amount=monthly_emi,
        status=LoanStatus.pending,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)

    logger.info(f"Loan applied: ₹{data.principal} by user {current_user.email} | EMI: ₹{monthly_emi}/month")
    return loan


@router.get("/my-loans", response_model=list[LoanResponse])
def get_my_loans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all loan applications made by the logged-in user."""
    return db.query(Loan).filter(Loan.user_id == current_user.id).all()


@router.post("/{loan_id}/approve", response_model=LoanResponse)
def approve_loan(
    loan_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin only: approve a pending loan application."""
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found.")
    if loan.status != LoanStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot approve — current status: {loan.status}.")

    loan.status = LoanStatus.approved
    loan.approved_by = admin.id
    db.commit()
    db.refresh(loan)

    logger.info(f"Loan {loan_id} approved by admin {admin.email}")
    return loan


@router.post("/{loan_id}/reject", response_model=LoanResponse)
def reject_loan(
    loan_id: int,
    data: LoanActionRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin only: reject a pending loan application with a reason."""
    loan = db.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail="Loan not found.")
    if loan.status != LoanStatus.pending:
        raise HTTPException(status_code=400, detail=f"Cannot reject — current status: {loan.status}.")
    if not data.rejection_reason:
        raise HTTPException(status_code=400, detail="Please provide a rejection reason.")

    loan.status = LoanStatus.rejected
    loan.approved_by = admin.id
    loan.rejection_reason = data.rejection_reason
    db.commit()
    db.refresh(loan)

    logger.info(f"Loan {loan_id} rejected by admin {admin.email}: {data.rejection_reason}")
    return loan


@router.get("/all", response_model=list[LoanResponse])
def get_all_loans(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin only: see all loan applications across all users."""
    return db.query(Loan).order_by(Loan.created_at.desc()).all()
