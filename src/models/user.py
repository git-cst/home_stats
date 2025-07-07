from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from models.token import TokenResponse

class UserRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    user_id: UUID
    email: str
    token_info: TokenResponse
    expires_in: datetime
    created_at: datetime
    updated_at: datetime

