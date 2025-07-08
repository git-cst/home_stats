from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from core.database import db_pool
from core.logging_setup import setup_logging
from db.repositories.user_repo import UserRepository
from services.user_cleanup import DataCleanupService
from api.v1.router import api_router

logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global cleanup_service
    
    # Startup
    await db_pool.initialize()
    
    # Initialize cleanup service
    user_repo = UserRepository(db_pool)
    cleanup_service = DataCleanupService(user_repo, grace_period_days=30)
    await cleanup_service.start_daily_cleanup()
    
    yield
    
    # Shutdown
    if cleanup_service:
        await cleanup_service.stop_cleanup()
    await db_pool.close()

    
app = FastAPI(
    title="Home_Stats_API",
    description="Personal music analytics and insights",
    version= "1.0.0",
    lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")