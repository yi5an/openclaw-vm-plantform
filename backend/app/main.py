"""
Main FastAPI application entry point.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import setup_exception_handlers
from app.api.v1 import auth, users, vms, agents
from app.infrastructure.database.base import init_db, close_db
from app.infrastructure.cache.redis_client import redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting OpenClaw VM Platform...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Initialize Redis
    await redis_client.connect()
    print("✅ Redis connected")
    
    # TODO: Initialize Libvirt connection
    
    yield
    
    # Shutdown
    print("🛑 Shutting down OpenClaw VM Platform...")
    
    # Close Redis
    await redis_client.disconnect()
    print("✅ Redis disconnected")
    
    # Close database
    await close_db()
    print("✅ Database connections closed")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="OpenClaw VM Platform API - 虚拟机租赁平台",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Setup exception handlers
setup_exception_handlers(app)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "app_name": settings.APP_NAME
    }


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to OpenClaw VM Platform API",
        "docs": "/api/docs",
        "health": "/health"
    }


# Include API routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["认证"]
)

app.include_router(
    users.router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["用户"]
)

app.include_router(
    vms.router,
    prefix=f"{settings.API_V1_PREFIX}/vms",
    tags=["虚拟机"]
)

app.include_router(
    agents.router,
    prefix=f"{settings.API_V1_PREFIX}/agents",
    tags=["Agent"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
