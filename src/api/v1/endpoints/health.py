from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime
import psycopg
import logging
import httpx
from enum import Enum

from models.server import HealthResponse, HealthStatus, ServiceCheck
from api.v1.deps import get_db_pool
from core.database import DatabasePool
from config.settings import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()

class ServiceName(str, Enum):
    DATABASE = "database"
    SPOTIFY_API = "spotify_api"
    GEMINI_API = "gemini_api"

@router.get("/health",
    summary="Health Check",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK
)
async def health_check(
    db: DatabasePool = Depends(get_db_pool)
):
    """Comprehensive health check for all critical services"""
    
    checks = HealthResponse(
        status=HealthStatus.HEALTHY,
        timestamp=datetime.utcnow().isoformat(),
        version="v1",
        services={}
    )

    # Run all health checks concurrently
    db_check = await _check_database(db)
    spotify_check = await _check_spotify_api()
    gemini_check = await _check_gemini_api()
    
    checks.services = {
        ServiceName.DATABASE: db_check,
        ServiceName.SPOTIFY_API: spotify_check,
        ServiceName.GEMINI_API: gemini_check
    }
    
    # Determine overall health status
    failed_services = [name for name, check in checks.services.items() 
                      if check.status == HealthStatus.UNHEALTHY]
    
    if failed_services:
        checks.status = HealthStatus.UNHEALTHY
        checks.message = f"Failed services: {', '.join(failed_services)}"
        logger.warning(f"Health check failed for services: {failed_services}")
        
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=checks.dict()
        )
    else:
        checks.status = HealthStatus.HEALTHY
        checks.message = "All systems operational"
        logger.debug("Health check passed for all services")

    return checks

async def _check_database(db: DatabasePool) -> ServiceCheck:
    """Check database connectivity and basic functionality"""
    start_time = datetime.now()
    
    try:
        async with db.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Test basic connectivity
                await cursor.execute("SELECT 1;")
                result = await cursor.fetchone()
                
                if not result or result[0] != 1:
                    return ServiceCheck(
                        status=HealthStatus.UNHEALTHY,
                        message="Database query returned unexpected result",
                        response_time_ms=_calculate_response_time(start_time)
                    )
                
                await cursor.execute("SELECT COUNT(*) FROM users;")
                await cursor.fetchone()

        if db._schema_initialized:
            return ServiceCheck(
                status=HealthStatus.HEALTHY,
                message="Database connection successful",
                response_time_ms=_calculate_response_time(start_time)
            )
        else:
            return ServiceCheck(
                status=HealthStatus.UNHEALTHY,
                message="Database schema not initialized",
                response_time_ms=_calculate_response_time(start_time)
            )
        
    except psycopg.OperationalError:
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message="Database connection failed",
            response_time_ms=_calculate_response_time(start_time)
        )
    except psycopg.DatabaseError as e:
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message=f"Database error: {str(e)[:100]}",  # Truncate long error messages
            response_time_ms=_calculate_response_time(start_time)
        )
    except Exception as e:
        logger.exception("Unexpected error during database health check")
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message=f"Unexpected database error: {type(e).__name__}",
            response_time_ms=_calculate_response_time(start_time)
        )

async def _check_spotify_api() -> ServiceCheck:
    """Check Spotify API availability"""
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Use Spotify's public endpoint that doesn't require auth
            response = await client.get("https://accounts.spotify.com/.well-known/openid_configuration")
            
            if response.status_code == 200:
                return ServiceCheck(
                    status=HealthStatus.HEALTHY,
                    message="Spotify API accessible",
                    response_time_ms=_calculate_response_time(start_time)
                )
            else:
                return ServiceCheck(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Spotify API returned status {response.status_code}",
                    response_time_ms=_calculate_response_time(start_time)
                )
                
    except httpx.TimeoutException:
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message="Spotify API timeout",
            response_time_ms=_calculate_response_time(start_time)
        )
    except Exception as e:
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message=f"Spotify API check failed: {type(e).__name__}",
            response_time_ms=_calculate_response_time(start_time)
        )

async def _check_gemini_api() -> ServiceCheck:
    """Check Gemini API availability"""
    start_time = datetime.now()
    settings = get_settings()
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # Basic connectivity check to Google AI API
            headers = {"x-goog-api-key": settings.gemini_api_key}
            response = await client.get(
                "https://generativelanguage.googleapis.com/v1beta/models",
                headers=headers
            )
            
            if response.status_code == 200:
                return ServiceCheck(
                    status=HealthStatus.HEALTHY,
                    message="Gemini API accessible",
                    response_time_ms=_calculate_response_time(start_time)
                )
            else:
                return ServiceCheck(
                    status=HealthStatus.UNHEALTHY,
                    message=f"Gemini API returned status {response.status_code}",
                    response_time_ms=_calculate_response_time(start_time)
                )
                
    except httpx.TimeoutException:
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message="Gemini API timeout",
            response_time_ms=_calculate_response_time(start_time)
        )
    except Exception as e:
        return ServiceCheck(
            status=HealthStatus.UNHEALTHY,
            message=f"Gemini API check failed: {type(e).__name__}",
            response_time_ms=_calculate_response_time(start_time)
        )

def _calculate_response_time(start_time: datetime) -> int:
    """Calculate response time in milliseconds"""
    return int((datetime.utcnow() - start_time).total_seconds() * 1000)