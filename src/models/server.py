from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
from typing import Optional

class HealthStatus(Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"

class ServiceCheck(BaseModel):
    status: HealthStatus
    message: str
    response_time_ms: int
    
class HealthResponse(BaseModel):
    status: HealthStatus = Field(None)
    timestamp: datetime = Field(default_factory = datetime.now)
    version: str = Field(None)
    message: Optional[str] = Field(None)
    services: Optional[dict[str, ServiceCheck]] = None
