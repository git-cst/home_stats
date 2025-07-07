from fastapi import APIRouter

from api.endpoints import auth, gemini, health, spotify

api_router = APIRouter(prefix="api/v1")

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(gemini.router, prefix="/gemini", tags=["gemini"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(spotify.router, prefix="/spotify" tags=["spotify"])