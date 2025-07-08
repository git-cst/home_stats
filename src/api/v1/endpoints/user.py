from fastapi import APIRouter, Depends, HTTPException, status, Path
from typing import Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime, timedelta

from api.v1.deps import require_permission, require_ownership_or_permission, get_user_repository

if TYPE_CHECKING:
    from core.permissions import Permission
    from db.repositories.user_repo import UserRepository

router = APIRouter()

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
    user_id: UUID = Path(..., description="ID of user to retrieve"),
    current_user: dict = Depends(require_ownership_or_permission(Permission.ADMIN_READ_ALL_USERS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get user profile - own profile or admin access"""
    user_data = await user_repo.get_user_by_id(user_id)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user_data

@router.post("/{user_id}/recover",
    status_code=status.HTTP_200_OK,
    summary="Recover soft-deleted account"
)
async def recover_account(
    user_id: UUID = Path(..., description="ID of the user to recover"),
    current_user: dict = Depends(require_ownership_or_permission(Permission.ADMIN_MANAGE_USERS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Recover a soft-deleted account within the grace period.
    Only the user themselves or an admin can recover an account.
    """
    
    # Check if account is soft-deleted and within grace period
    user = await user_repo.get_user_by_id(user_id, include_deleted=True)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("is_active", True):
        raise HTTPException(status_code=400, detail="Account is not deleted")
    
    deleted_at = user.get("deleted_at")
    if not deleted_at:
        raise HTTPException(status_code=400, detail="Account was not soft-deleted")
    
    # Check if still within grace period (30 days)
    grace_period = timedelta(days=30)
    if datetime.utcnow() - deleted_at > grace_period:
        raise HTTPException(
            status_code=410, 
            detail="Grace period expired. Account cannot be recovered."
        )
    
    # Recover the account
    success = await user_repo.recover_user(user_id)
    if success:
        return {"message": "Account successfully recovered"}
    else:
        raise HTTPException(status_code=500, detail="Failed to recover account")