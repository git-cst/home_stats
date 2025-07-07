from fastapi import HTTPException, status
from typing import Optional
from datetime import datetime

from db.repositories.user_repo import UserRepository
from models.token import TokenResponse, TokenRefreshResponse
from core.security import create_access_token, create_refresh_token, verify_password, verify_token
from config.settings import get_settings

class AuthService:
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        user = await self.user_repo.get_user_by_email(email)
        if not user or not verify_password(password, user['hashed_password']):
            return None
        return user

    async def register_user(self, email: str, password: str):
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

