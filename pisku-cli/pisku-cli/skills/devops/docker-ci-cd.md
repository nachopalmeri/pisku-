# Docker + CI/CD

## Purpose
Multi-stage Dockerfiles, Docker Compose for local dev, and GitHub Actions pipelines for automated deploy.

## Multi-Stage Dockerfile (Python)
```dockerfile
# Stage 1: build/dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: runtime (smaller image)
FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /install /usr/local
COPY . .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose (local dev)
```yaml
services:
  api:
    build: .
    ports: ["8000:8000"]
    volumes: ["./:/app"]         # hot reload
    environment:
      - DATABASE_URL=postgresql://postgres:secret@db:5432/myapp
      - ENV=development
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secret
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

volumes:
  pgdata:
```

## GitHub Actions — Deploy to Railway
```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: pytest --tb=short

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: railwayapp/railway-action@v1
        with:
          service: my-service
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## .dockerignore
```
__pycache__/
*.pyc
.env
.git
node_modules/
*.md
tests/
```

## Key Commands
```bash
docker build -t myapp:latest .
docker compose up -d          # detached
docker compose logs -f api    # follow logs
docker compose exec api bash  # shell into container
docker system prune -af       # cleanup
```
