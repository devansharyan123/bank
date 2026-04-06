"""Tests for user registration, login, and KYC."""


def test_register_new_user(client):
    response = client.post("/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secret123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "alice@example.com"
    assert data["kyc_verified"] is False


def test_register_duplicate_email(client):
    client.post("/auth/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "password": "password123",
    })
    # Second registration with same email should fail
    response = client.post("/auth/register", json={
        "name": "Bob2",
        "email": "bob@example.com",
        "password": "password456",
    })
    assert response.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={
        "name": "Carol",
        "email": "carol@example.com",
        "password": "mypassword",
    })
    response = client.post("/auth/login", json={
        "email": "carol@example.com",
        "password": "mypassword",
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "name": "Dave",
        "email": "dave@example.com",
        "password": "correctpass",
    })
    response = client.post("/auth/login", json={
        "email": "dave@example.com",
        "password": "wrongpass",
    })
    assert response.status_code == 401


def test_kyc_verification(client):
    client.post("/auth/register", json={
        "name": "Eve",
        "email": "eve@example.com",
        "password": "pass1234",
    })
    login = client.post("/auth/login", json={"email": "eve@example.com", "password": "pass1234"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/auth/kyc", json={
        "aadhaar_number": "1234-5678-9012",
        "pan_number": "ABCDE1234F",
    }, headers=headers)
    assert response.status_code == 200
    assert response.json()["kyc_verified"] is True


def test_kyc_invalid_aadhaar(client):
    client.post("/auth/register", json={"name": "Frank", "email": "frank@example.com", "password": "pass1234"})
    login = client.post("/auth/login", json={"email": "frank@example.com", "password": "pass1234"})
    token = login.json()["access_token"]

    response = client.post("/auth/kyc", json={
        "aadhaar_number": "12345678",   # wrong format
        "pan_number": "ABCDE1234F",
    }, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422  # Pydantic validation error
