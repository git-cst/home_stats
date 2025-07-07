from pydantic import BaseModel, Field
from datetime import datetime

class TokenResponse(BaseModel):
    token: str
    token_type : str = Field(default = "Bearer")
    refresh_token: str
    expires_in: int
    created_at: datetime

class TokenRefreshResponse(BaseModel):
    refresh_token: str
    expires_in: int
    created_at: datetime