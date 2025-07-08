from fastapi import Depends, HTTPException
from typing import TYPE_CHECKING, Optional

from core.database import db_pool, DatabasePool
from core.security import get_current_user
from db.repositories.user_repo import UserRepository
from services.auth import AuthService

if TYPE_CHECKING:
    from core.permissions import Permission
    from models.user import UserResponse

async def get_db_pool() -> DatabasePool:
    """Dependency that returns the database pool"""
    return db_pool

async def get_user_repository(pool: DatabasePool = Depends(get_db_pool)) -> UserRepository:
    """Dependency that creates and returns a UserRepository instance"""
    return UserRepository(pool)  

async def get_auth_service(user_repo: UserRepository = Depends(get_user_repository)) -> AuthService:
    """Dependency that creates and returns a AuthService instance"""
    return AuthService(user_repo)

def require_permission(permission: Permission):
    """Create a dependency that requires a specific permission"""
    async def permission_dependency(
        current_user: UserResponse = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service)
    ):
        await auth_service.require_permission(current_user.id, permission)
        return current_user
    
    return permission_dependency

def require_ownership_or_permission(admin_permission: Optional[Permission] = None):
    """Create a dependency that requires resource ownership or admin permission"""
    async def ownership_dependency(
        resource_user_id: int,
        current_user: dict = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service)
    ):
        await auth_service.require_resource_ownership(
            current_user["id"], 
            resource_user_id, 
            admin_permission
        )
        return current_user
    
    return ownership_dependency