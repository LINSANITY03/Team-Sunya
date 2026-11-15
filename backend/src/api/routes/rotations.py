
from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.location_service import is_inside_nepal

class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

router = APIRouter(prefix="/rotations", tags=["Rotations"])

@router.post("/recommend")
def recommend_rotations(location: Location):
    """
    Receive and validate frontend coordinates.
    """

    latitude = location.latitude
    longitude = location.longitude

    print(f"Received latitude: {latitude}")
    print(f"Received longitude: {longitude}")

    return {
        "status": "success",
        "message": "Coordinates received successfully.",
        "latitude": latitude,
        "longitude": longitude,
        "is_nepal": is_inside_nepal(latitude, longitude)
    }
