from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime
from uuid import UUID

from db.repositories.user_repo import UserRepository
from models.token import TokenResponse, TokenRefreshResponse
from core.security import create_access_token, create_refresh_token, verify_password, verify_token
from core.permissions import Permission, Role, ROLE_PERMISSIONS
from config.settings import get_settings

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Authenticate whether the user exists and the credentials provided are correct"""
        user = await self.user_repo.get_user_by_email(email)
        if not user or not verify_password(password, user['hashed_password']):
            return None
        return user

    async def get_user_permissions(self, user_id: UUID) -> list[Permission]:
        """Get all permissions for a user (role-based + explicit)"""
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            return []
        
        role = Role(user.get('role', 'user'))
        role_permissions = ROLE_PERMISSIONS.get(role, [])

        # Get explicit permissions from database
        explicit_permissions = await self.user_repo.get_user_permissions(user_id)
        
        # Combine and deduplicate
        all_permissions = list(set(role_permissions + explicit_permissions))
        return all_permissions

    async def user_has_permission(self, user_id: int, permission: Permission) -> bool:
        """Check if user has a specific permission"""
        user_permissions = await self.get_user_permissions(user_id)
        return permission in user_permissions
    
    async def require_permission(self, user_id: int, permission: Permission) -> None:
        """Raise exception if user doesn't have permission"""
        if not await self.user_has_permission(user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required: {permission.value}"
            )
        
    async def require_resource_ownership(
        self, 
        user_id: int, 
        resource_user_id: int, 
        admin_permission: Optional[Permission] = None
    ) -> None:
        """Ensure user owns resource or has admin permission"""
        if user_id == resource_user_id:
            return  # User owns the resource
        
        if admin_permission:
            # Check if user has admin permission to access any user's resources
            if await self.user_has_permission(user_id, admin_permission):
                return
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own resources"
        )

    async def register_user(self, email: str, password: str):
        """Register a user using the given email and password"""
        existing_user = await self.user_repo.get_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists"
            )
        
        if len(password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        user_id = await self.user_repo.create_user(email, password)
        
        # Return the created user data
        user = await self.user_repo.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        return user

    async def create_tokens(self, user_id):
        """Create the JWT access token and refresh token"""
        settings = get_settings()
        
        access_token = create_access_token(data = {"sub": str(user_id)})
        refresh_token = create_refresh_token(data = {"sub": str(user_id)})

        return TokenResponse(
            token = access_token,
            refresh_token = refresh_token,
            token_type = "bearer",
            expires_in = settings.access_token_expiry_minutes * 60
        )

    async def refresh_access_token(self, refresh_token):
        """Refresh the JWT access token and refresh token"""
        payload = verify_token(refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        # Verify user still exists and is active
        user = await self.user_repo.get_user_by_id(int(user_id))
        if not user:
            return None
        
        return self.create_tokens(int(user_id))

