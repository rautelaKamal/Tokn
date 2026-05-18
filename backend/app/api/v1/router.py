from fastapi import APIRouter

from app.api.v1 import health, optimize

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(optimize.router, prefix="/optimize", tags=["optimize"])
