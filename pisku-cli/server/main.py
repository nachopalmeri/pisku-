"""
PISKU Server — FastAPI backend
Responsabilidades:
  1. Validar licencias PRO (endpoint que llama el CLI)
  2. Procesar pagos Stripe (checkout + webhooks)
  3. Servir la Landing Page (HTML estático)
"""

from contextlib import asynccontextmanager
from pathlib import Path

import stripe
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from server.routers import licenses, payments, health
from server.config import settings
from server.db import init_db

ROOT = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    stripe.api_key = settings.stripe_secret_key
    print(f"✅ PISKU Server starting — ENV: {settings.env}")
    yield
    # Shutdown (cleanup si hace falta)
    print("🛑 PISKU Server shutting down")


app = FastAPI(
    title="PISKU API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# API Routers
app.include_router(health.router,   prefix="/api")
app.include_router(licenses.router, prefix="/api/licenses")
app.include_router(payments.router, prefix="/api/payments")

# Serve landing page (HTML/CSS/JS estático)
landing_path = ROOT.parent / "landing"
if landing_path.exists():
    app.mount("/", StaticFiles(directory=str(landing_path), html=True), name="landing")
