from fastapi import Depends
from core.database import db_pool, DatabasePool
from db.repositories.user_repo import UserRepository
from services.auth import AuthService

async def get_db_pool() -> DatabasePool:
    """Dependency that returns the database pool"""
    return db_pool

async def get_user_repository(pool: DatabasePool = Depends(get_db_pool)) -> UserRepository:
    """Dependency that creates and returns a UserRepository instance"""
    return UserRepository(pool)  

async def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    """Dependency that creates and returns a AuthService instance"""
    return AuthService(user_repo)