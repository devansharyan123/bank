from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from models.enums import UserRole
from schemas.auth import RegisterRequest, LoginRequest, TokenResponse, KYCRequest, UserResponse
from utils.security import hash_password, verify_password, create_access_token, get_current_user
from utils.logger import logger

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new customer account.

    Steps:
    1. Check the email is not already registered
    2. Hash the password
    3. Save the new user
    """
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with email '{data.email}' already exists.",
        )

    new_user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=UserRole.customer,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {new_user.email}")
    return new_user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """
    Verify credentials and return a JWT token.

    Steps:
    1. Find the user by email
    2. Verify the password
    3. Return a JWT token
    """
    user = db.query(User).filter(User.email == data.email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="No account found with that email address.")

    if not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password.")

    token = create_access_token(data={"sub": str(user.id)})
    logger.info(f"User logged in: {user.email}")
    return TokenResponse(access_token=token)


@router.post("/kyc", response_model=UserResponse)
def submit_kyc(
    data: KYCRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Submit Aadhaar and PAN for KYC verification.

    Required before the user can open a bank account.
    In a real system this would call a government API — here we validate the format.
    """
    if current_user.kyc_verified:
        raise HTTPException(status_code=400, detail="KYC is already verified for this account.")

    current_user.aadhaar_number = data.aadhaar_number
    current_user.pan_number = data.pan_number
    current_user.kyc_verified = True

    db.commit()
    db.refresh(current_user)

    logger.info(f"KYC verified for user: {current_user.email}")
    return current_user


@router.get("/me", response_model=UserResponse)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get the profile of the currently logged-in user."""
    return current_user
