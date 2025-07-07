from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from services.auth import AuthService
from api.deps import get_auth_service
from models.user import UserRequest, UserResponse
from models.token import TokenResponse

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



@router.post("/refresh", response_model=TokenResponse)
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