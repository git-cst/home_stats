from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.core.database import db_pool
from src.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Ensure that the database connection pool is initialized and closed properly"""
    db_pool.initialize()
    yield
    db_pool.close()
    
app = FastAPI(
    title="Home_Stats_API",
    description="Personal music analytics and insights",
    version= "1.0.0",
    lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")