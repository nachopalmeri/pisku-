# Python FastAPI — Patterns & Conventions

## Purpose
Context for building REST APIs with FastAPI. Use when the project involves API endpoints, Pydantic validation, dependency injection, or async routes.

## Project Structure
```
app/
├── main.py          # FastAPI app + router includes
├── routers/         # One file per domain (users.py, items.py)
├── models/          # SQLAlchemy or Pydantic models
├── schemas/         # Pydantic request/response schemas
├── dependencies.py  # Shared dependencies (db, auth)
└── config.py        # Settings via pydantic-settings
```

## Key Patterns

### Route Definition
```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
```

### Dependency Injection
```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    secret_key: str
    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Error Handling
- Use `HTTPException` for expected errors (404, 403, 422)
- Use exception handlers for unexpected errors
- Always return typed response_model, never raw dicts

### Async Best Practices
- Use `async def` for I/O-bound routes (DB, HTTP calls)
- Use `def` for CPU-bound or sync libraries
- Don't mix sync DB calls in async routes without `run_in_executor`

## Testing Pattern
```python
from fastapi.testclient import TestClient
client = TestClient(app)

def test_get_user():
    response = client.get("/users/1")
    assert response.status_code == 200
```

## Common Mistakes to Avoid
- Never put business logic in routes — use service layer
- Never return raw SQLAlchemy objects — use schemas
- Never hardcode secrets — use Settings
- Never use `print()` — use `logging`
