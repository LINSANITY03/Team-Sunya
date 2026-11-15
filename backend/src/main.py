import logging

from contextlib import asynccontextmanager
from api.routes.health import router as health_router
from api.routes.rotations import router as recommendation_router

from fastapi import FastAPI

from core.logging import setup_logging
from database.connection import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting Crop Rotation API")

    init_db()
    logger.info("Database initialized successfully")
    yield

    logger.info("Shutting down Crop Rotation API")

app = FastAPI(
    title="Crop Rotation API",
    version="1.0.0",
    description="Crop Rotation Recommendation API",
    lifespan=lifespan,
)

# API routes.
app.include_router(
    recommendation_router
)
app.include_router(
    health_router
)


@app.get("/")
async def root():
    return {
        "message": "Crop Rotation Recommendation API",
        "status": "running",
    }
