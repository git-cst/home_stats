
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body, Query
from typing import Optional, TYPE_CHECKING
from uuid import UUID

from services.auth import AuthService
from services.user_cleanup import cleanup_service
from core.database import db_pool
from models.permission import PermissionGrantRequest, PermissionRevokeRequest, UserPermissionsResponse
from api.v1.deps import get_auth_service, require_permission, require_ownership_or_permission, get_user_repository

if TYPE_CHECKING:
    from core.permissions import Permission
    from db.repositories.user_repo import UserRepository

router = APIRouter()

#=====================================================================
# USER RELATED ADMIN COMMANDS
#=====================================================================

@router.delete("/users/{user_id}",
    status_code=status.HTTP_202_ACCEPTED,  # 202 for async processing
    summary="Delete user account (GDPR compliant)"
)
async def delete_user(
    user_id: UUID = Path(..., description="ID of the user to delete"),
    hard_delete: bool = Query(False, description="Immediately delete all data (admin only)"),
    current_user: dict = Depends(require_ownership_or_permission(Permission.ADMIN_DELETE_ANY_USER)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """
    Delete user account in compliance with GDPR Article 17.
    
    - Users can delete their own accounts
    - Admins can delete any account
    - By default, performs soft delete with 30-day grace period
    - Admin can force immediate hard delete
    """
    
    # Check if user exists
    target_user = await user_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Only admins can perform hard delete immediately
    if hard_delete:
        if not await user_repo.user_has_permission(
            UUID(current_user["id"]), 
            Permission.ADMIN_DELETE_ANY_USER
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hard delete requires admin privileges"
            )
        
        await user_repo.hard_delete_user(user_id)
        return {"message": "User permanently deleted", "type": "hard_delete"}
    
    else:
        # Soft delete - standard for user self-deletion
        await user_repo.soft_delete_user(user_id)
        return {
            "message": "Account deactivated. Data will be permanently deleted in 30 days.", 
            "type": "soft_delete",
            "grace_period_days": 30
        }


@router.post("/users/{user_id}/permissions",             
    status_code = status.HTTP_200_OK,
    summary="Requires admin priviledges in order to grant a user a new permssion"
)
async def grant_permission(
    user_id: UUID = Path(..., title="ID for the user"),
    permission_request: PermissionGrantRequest = Body(..., title="The permission enum value to be granted to the user", example=Permission.USER_READ_OWN_PROFILE), 
    current_user: dict = Depends(require_permission(Permission.ADMIN_MANAGE_PERMISSIONS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Grant permission to a user (admin only)"""
    # Check if user exists
    target_user = await user_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user already has this permission
    if await user_repo.user_has_permission(user_id, permission_request.permission):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User already has permission: {permission_request.permission.value}"
        )

    result = await user_repo.grant_user_permission(
        user_id, 
        permission_request.permission,
        UUID(current_user["id"])
    )
    return {
        "message": f"Permission {permission_request.permission.value} granted to user {user_id}",
        "granted_permission": result
    }

@router.post("/users/{user_id}/permissions",             
    status_code = status.HTTP_200_OK,
    summary="Requires admin priviledges in order to grant a user a new permssion"
)
async def revoke_permsission(
    user_id: UUID = Path(..., title="ID for the user"),
    permission_request: PermissionRevokeRequest = Body(..., title="The permission enum value to be revoked from the user", example=Permission.USER_READ_OWN_PROFILE), 
    current_user: dict = Depends(require_permission(Permission.ADMIN_MANAGE_PERMISSIONS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Revoke permission from a user (admin only)"""
    # Check if user exists
    target_user = await user_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    success = await user_repo.revoke_user_permission(user_id, permission_request.permission)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User does not have permission: {permission_request.permission.value}"
        )
    
    return {
        "message": f"Permission {permission_request.permission.value} revoked from user {user_id}"
    }

@router.get("/users/{user_id}/permissions",
    response_model=UserPermissionsResponse,
    summary="Get all permissions for a user (Admin only)"
)
async def get_user_permissions(
    user_id: UUID = Path(..., description="ID of the user to get permissions for"),
    current_user: dict = Depends(require_permission(Permission.ADMIN_MANAGE_PERMISSIONS)),
    user_repo: UserRepository = Depends(get_user_repository)
):
    """Get all permissions for a user (admin only)"""
    # Check if user exists
    target_user = await user_repo.get_user_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    permissions = await user_repo.get_user_permissions(user_id)
    permission_strings = [perm['permission'] for perm in permissions]
    
    return UserPermissionsResponse(
        user_id=user_id,
        permissions=permission_strings
    )

#=====================================================================
# DATABASE RELATED ADMIN COMMANDS
#=====================================================================

@router.post("/cleanup/manual")
async def manual_cleanup(
    current_user: dict = Depends(require_permission(Permission.ADMIN_MANAGE_SYSTEM))
):
    """Manually trigger cleanup (useful for testing or immediate cleanup)"""
    if not cleanup_service:
        raise HTTPException(status_code=503, detail="Cleanup service not available")
    
    result = await cleanup_service.manual_cleanup()
    return {"message": "Manual cleanup completed", "results": result}

@router.get("/cleanup/info")
async def cleanup_info(
    current_user: dict = Depends(require_permission(Permission.ADMIN_VIEW_SYSTEM_STATS))
):
    """Get detailed cleanup service information"""
    if not cleanup_service:
        raise HTTPException(status_code=503, detail="Cleanup service not available")
    
    # Calculate time until next cleanup
    next_cleanup_in = None
    if cleanup_service.next_cleanup:
        delta = cleanup_service.next_cleanup - datetime.utcnow()
        next_cleanup_in = max(0, int(delta.total_seconds()))  # Don't show negative
    
    return {
        "grace_period_days": cleanup_service.grace_period_days,
        "status": "running" if cleanup_service._task and not cleanup_service._task.done() else "stopped",
        "next_cleanup": cleanup_service.next_cleanup.isoformat() if cleanup_service.next_cleanup else None,
        "next_cleanup_in_seconds": next_cleanup_in,
        "last_cleanup": cleanup_service.last_cleanup.isoformat() if cleanup_service.last_cleanup else None,
        "last_cleanup_result": cleanup_service.last_cleanup_result
    }

@router.get("/cleanup/stats")
async def cleanup_stats(
    current_user: dict = Depends(require_permission(Permission.ADMIN_VIEW_SYSTEM_STATS))
):
    """Get cleanup statistics and health"""
    if not cleanup_service:
        raise HTTPException(status_code=503, detail="Cleanup service not available")
    
    # Get current count of users pending deletion
    user_repo = UserRepository(db_pool)
    cutoff_date = datetime.utcnow() - timedelta(days=cleanup_service.grace_period_days)
    pending_deletions = await user_repo.get_expired_soft_deleted_users(cutoff_date)
    
    # Check if cleanup is overdue
    is_overdue = False
    overdue_hours = 0
    if cleanup_service.next_cleanup:
        overdue_delta = datetime.utcnow() - cleanup_service.next_cleanup
        if overdue_delta.total_seconds() > 0:
            is_overdue = True
            overdue_hours = overdue_delta.total_seconds() / 3600
    
    return {
        "users_pending_deletion": len(pending_deletions),
        "cleanup_overdue": is_overdue,
        "overdue_hours": round(overdue_hours, 2) if is_overdue else 0,
        "service_healthy": not is_overdue and cleanup_service._task and not cleanup_service._task.done()
    }

#=====================================================================
# SPOTIFY RELATED ADMIN COMMANDS
#=====================================================================