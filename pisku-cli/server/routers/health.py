from fastapi import APIRouter
from server.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.env,
        "version": "0.1.0",
    }
