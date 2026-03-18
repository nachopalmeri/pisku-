# Testing with Pytest

## Purpose
Pytest setup, fixtures, mocking, and coverage for Python projects.

## Setup
```bash
pip install pytest pytest-cov pytest-asyncio httpx
```
```ini
# pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = --tb=short --cov=app --cov-report=term-missing
```

## Fixtures
```python
import pytest
from httpx import AsyncClient
from app.main import app
from app.db import get_db

@pytest.fixture
def db_session():
    """In-memory SQLite for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)

@pytest.fixture
async def client(db_session):
    """Async test client with DB override."""
    app.dependency_overrides[get_db] = lambda: db_session
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_user(db_session):
    user = User(email="test@test.com", hashed_password="hash")
    db_session.add(user)
    db_session.commit()
    return user
```

## Test Patterns
```python
# Basic test
def test_create_user(client, db_session):
    response = client.post("/users", json={"email": "a@b.com", "password": "pass123"})
    assert response.status_code == 201
    assert response.json()["email"] == "a@b.com"

# Parametrize
@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("not-an-email", False),
    ("", False),
])
def test_email_validation(email, valid):
    assert validate_email(email) == valid

# Async test
@pytest.mark.asyncio
async def test_async_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
```

## Mocking
```python
from unittest.mock import patch, AsyncMock

def test_sends_email(client):
    with patch("app.services.email.send") as mock_send:
        mock_send.return_value = True
        response = client.post("/register", json={"email": "a@b.com"})
        assert mock_send.called
        mock_send.assert_called_once_with("a@b.com", subject="Welcome")

# Mock external API
@patch("httpx.AsyncClient.get", new_callable=AsyncMock)
async def test_external_api(mock_get):
    mock_get.return_value.json.return_value = {"price": 100}
    result = await fetch_price("BTC")
    assert result == 100
```

## Coverage
```bash
pytest --cov=app --cov-report=html   # generates htmlcov/
pytest --cov=app --cov-fail-under=80 # fail if < 80%
```

## Key Patterns
- One assertion per test when possible
- Use fixtures for DB, clients, and shared state
- `conftest.py` for shared fixtures across modules
- Mock at the boundary (external APIs, email, etc.)
- Test edge cases: empty inputs, None, large numbers
