import re
from pydantic import BaseModel, EmailStr, field_validator


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_must_be_strong_enough(cls, value: str) -> str:
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class KYCRequest(BaseModel):
    """
    Aadhaar format: XXXX-XXXX-XXXX
    PAN format    : ABCDE1234F
    """
    aadhaar_number: str
    pan_number: str

    @field_validator("aadhaar_number")
    @classmethod
    def validate_aadhaar(cls, value: str) -> str:
        if not re.match(r"^\d{4}-\d{4}-\d{4}$", value):
            raise ValueError("Aadhaar must be in XXXX-XXXX-XXXX format (e.g., 1234-5678-9012).")
        return value

    @field_validator("pan_number")
    @classmethod
    def validate_pan(cls, value: str) -> str:
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", value.upper()):
            raise ValueError("PAN must be in ABCDE1234F format (e.g., ABCDE1234F).")
        return value.upper()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    kyc_verified: bool

    model_config = {"from_attributes": True}
