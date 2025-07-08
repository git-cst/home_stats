from fastapi import APIRouter

from api.v1.endpoints import admin, auth, gemini, health, spotify, user

api_router = APIRouter(prefix="api/v1")

api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(gemini.router, prefix="/gemini", tags=["gemini"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(spotify.router, prefix="/spotify", tags=["spotify"])
api_router.include_router(user.router, prefix="/users", tags=["users"])