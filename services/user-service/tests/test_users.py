import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database import get_db, Base

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_user():
    response = client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepassword123",
        "full_name": "Test User"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"


def test_register_duplicate_email():
    client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "password123",
        "full_name": "User One"
    })
    response = client.post("/auth/register", json={
        "email": "dup@example.com",
        "password": "password456",
        "full_name": "User Two"
    })
    assert response.status_code == 400


def test_login():
    client.post("/auth/register", json={
        "email": "login@example.com",
        "password": "password123",
        "full_name": "Login User"
    })
    response = client.post("/auth/token", data={
        "username": "login@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials():
    response = client.post("/auth/token", data={
        "username": "nouser@example.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401
