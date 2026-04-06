"""Tests for loan application, EMI calculation, and admin approval/rejection."""

from decimal import Decimal


ADMIN_EMAIL = "admin_loans@test.com"
CUSTOMER_EMAIL = "borrower@test.com"


def setup_admin(client):
    """Register a user and manually set their role to admin via direct DB — or use a seed endpoint."""
    # For testing, we register a normal user and promote via a helper
    from sqlalchemy.orm import Session
    from tests.conftest import TestSessionLocal
    from models.user import User
    from models.enums import UserRole

    client.post("/auth/register", json={"name": "Admin", "email": ADMIN_EMAIL, "password": "adminpass"})
    db: Session = TestSessionLocal()
    try:
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if user:
            user.role = UserRole.admin
            user.kyc_verified = True
            db.commit()
    finally:
        db.close()

    login = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "adminpass"})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def setup_customer(client):
    client.post("/auth/register", json={"name": "Borrower", "email": CUSTOMER_EMAIL, "password": "pass1234"})
    login = client.post("/auth/login", json={"email": CUSTOMER_EMAIL, "password": "pass1234"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/auth/kyc", json={"aadhaar_number": "9876-5432-1098", "pan_number": "XYZAB9876C"}, headers=headers)
    return headers


def test_emi_calculation_no_login_required(client):
    """EMI calculator endpoint should work without authentication."""
    response = client.post("/loans/calculate-emi", json={
        "principal": 100000,
        "annual_rate": 10,
        "tenure_months": 12,
    })
    assert response.status_code == 200
    data = response.json()
    # EMI for ₹1,00,000 at 10% for 12 months ≈ ₹8,791.59
    assert float(data["monthly_emi"]) == pytest.approx(8791.59, rel=0.01)
    assert float(data["total_interest"]) > 0


def test_apply_for_loan(client):
    headers = setup_customer(client)
    response = client.post("/loans/apply", json={
        "principal": 50000,
        "annual_rate": 12,
        "tenure_months": 24,
    }, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert float(data["emi_amount"]) > 0


def test_admin_approve_loan(client):
    customer_headers = setup_customer(client)
    admin_headers = setup_admin(client)

    loan = client.post("/loans/apply", json={
        "principal": 30000,
        "annual_rate": 10,
        "tenure_months": 12,
    }, headers=customer_headers).json()

    response = client.post(f"/loans/{loan['id']}/approve", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_admin_reject_loan_with_reason(client):
    customer_headers = setup_customer(client)
    admin_headers = setup_admin(client)

    loan = client.post("/loans/apply", json={
        "principal": 500000,
        "annual_rate": 8,
        "tenure_months": 60,
    }, headers=customer_headers).json()

    response = client.post(f"/loans/{loan['id']}/reject", json={
        "rejection_reason": "Credit score too low.",
    }, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert "Credit score" in response.json()["rejection_reason"]


def test_customer_cannot_approve_loan(client):
    """A regular customer should not be able to approve loans."""
    customer_headers = setup_customer(client)
    loan = client.post("/loans/apply", json={
        "principal": 20000,
        "annual_rate": 9,
        "tenure_months": 6,
    }, headers=customer_headers).json()

    response = client.post(f"/loans/{loan['id']}/approve", headers=customer_headers)
    assert response.status_code == 403


import pytest
