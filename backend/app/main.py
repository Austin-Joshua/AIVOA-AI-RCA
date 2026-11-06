from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import check_database_connection
from app.api.api_v1 import api_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("aivoa-rca")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing AIVOA.AI RCA Intelligence backend...")
    await check_database_connection()
    logger.info("Database connectivity verified.")
    if settings.INITIAL_ADMIN_USERNAME and settings.INITIAL_ADMIN_PASSWORD:
        from app.services.admin_provisioning import provision_admin_account
        from app.core.database import AsyncSessionLocal
        if AsyncSessionLocal:
            async with AsyncSessionLocal() as db:
                await provision_admin_account(
                    db=db,
                    username=settings.INITIAL_ADMIN_USERNAME,
                    password=settings.INITIAL_ADMIN_PASSWORD,
                    email=settings.INITIAL_ADMIN_EMAIL,
                    full_name=settings.INITIAL_ADMIN_FULL_NAME
                )
    yield
    logger.info("Shutting down AIVOA.AI RCA Intelligence backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="AI-Powered Root Cause Analysis (RCA) Module for Pharmaceutical API Manufacturing",
    lifespan=lifespan
)

# CORS Middleware with explicit allowlist (Wildcard prohibited with allow_credentials=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include v1 API
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "database": "connected"
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to AIVOA.AI RCA Intelligence API",
        "docs": "/docs",
        "openapi": "/openapi.json"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

