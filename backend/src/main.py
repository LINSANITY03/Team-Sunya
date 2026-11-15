from api.routes.health import router as health_router
from api.routes.rotations import router as recommendation_router
from fastapi import FastAPI

app = FastAPI(
    title="Crop Rotation API",
    version="1.0.0",
    description="Crop Rotation Recommendation API",
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
