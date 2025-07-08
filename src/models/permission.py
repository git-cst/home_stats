from pydantic import BaseModel, ConfigDict
from uuid import UUID

from core.permissions import Permission

class PermissionGrantRequest(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "permission": "read:own_profile"
            }
        }
    )

    permission: Permission

class PermissionRevokeRequest(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "permission": "read:own_profile"
            }
        }
    )
    permission: Permission

class UserPermissionsResponse(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "permission": "read:own_profile"
            }
        }
    )

    user_id: UUID
    permissions: list[str]