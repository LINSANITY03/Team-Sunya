
from fastapi import APIRouter

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("/")
def health_check() -> dict[str, str]:
    """Check whether the API is running."""
    return {
        "status": "healthy",
        "service": "crop-rotation-api",
    }
