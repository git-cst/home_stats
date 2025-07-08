from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from services.auth import AuthService
from api.deps import get_auth_service, require_permission, require_ownership_or_permission, get_user_repository
from models.user import UserRequest, UserResponse
from models.token import TokenResponse

if TYPE_CHECKING:
    from core.permissions import Permission
    from db.repositories.user_repo import UserRepository

router = APIRouter()

@router.post("/register",
    response_model = UserResponse,
    status_code = status.HTTP_201_CREATED
)
async def register(
    user_data: UserRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Register a new user"""
    user = await auth_service.register_user(user_data.email, user_data.password)
    return UserResponse(**user)

@router.post("/login",
    response_model= TokenResponse,
    status_code = status.HTTP_200_OK
)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login and get JWT tokens"""
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return auth_service.create_tokens(user['id'])

@router.post("/refresh",
    response_model=TokenResponse,
    status_code = status.HTTP_200_OK
)
async def refresh_token(
    refresh_token: str,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token"""
    tokens = await auth_service.refresh_access_token(refresh_token)
    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    return tokens

@router.get("/me",
    status_code = status.HTTP_200_OK
)
async def get_my_profile(
    current_user: dict = Depends(require_permission(Permission.USER_READ_OWN_PROFILE))
):
    """Get current user's profile"""
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "role": current_user.get("role", "user")
    }

@router.get("/{user_id}",
    status_code = status.HTTP_200_OK
)
async def get_user_profile(
    user_id: UUID,
    current_user: dict = Depends(require_ownership_or_permission(Permission.ADMIN_READ_ALL_USERS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user profile - own profile or admin access"""
    user_data = await user_repo.get_user_by_id(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_data

@router.post("/{user_id}/permissions",             
    status_code = status.HTTP_200_OK
)
async def grant_permission(
    user_id: UUID,
    permission_request: dict,  # e.g., {"permission": "read:all_users"}
    current_user: dict = Depends(require_permission(Permission.ADMIN_MANAGE_PERMISSIONS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Grant permission to a user (admin only)"""
    permission = Permission(permission_request["permission"])
    result = await user_repo.grant_user_permission(
        user_id, 
        permission, 
        UUID(current_user["id"])
    )
    return {"message": f"Permission {permission.value} granted to user {user_id}"}