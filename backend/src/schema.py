
from datetime import date

from pydantic import BaseModel, Field, field_validator


class RecommendationRequest(BaseModel):
    """Complete input required to generate crop rotation recommendations."""

    # Field identification and location
    field_id: str = Field(min_length=1, max_length=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    irrigation: bool = False

    # Field and soil thresholds
    bd_reject: float = Field(ge=0)
    clay_max_root_crops: float = Field(ge=0, le=100)
    min_soil_depth_ratio: float = Field(ge=0, le=1)
    min_wet_high: float = Field(ge=0, le=1)
    min_wet_low: float = Field(ge=0, le=1)
    n_ok_g_per_kg: float = Field(ge=0)
    rain_eff: float = Field(ge=0, le=1)
    water_reject_ratio: float = Field(ge=0, le=1)

    # Rotation configuration
    cyclic: bool = True
    default_family_gap: int = Field(default=2, ge=0)
    harvest_mismatch_tol_days: int = Field(default=20, ge=0)
    max_candidates: int = Field(default=50000, ge=1)
    max_fallow_days: int = Field(default=120, ge=0)
    max_horizon_days: int = Field(default=800, ge=1)
    max_single_crop_days: int = Field(default=300, ge=1)
    require_legume: bool = False
    rotation_length: int = Field(default=3, ge=1)
    start_date: date
    turnaround_days: int = Field(default=10, ge=0)

    # Farmer priorities
    food_security: float = Field(default=0.3, ge=0)
    low_risk: float = Field(default=0.5, ge=0)
    profit: float = Field(default=0.5, ge=0)
    soil_health: float = Field(default=0.2, ge=0)
    water_saving: float = Field(default=0.25, ge=0)

    @field_validator("field_id")
    @classmethod
    def validate_field_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field_id cannot be empty.")
        return value

    @field_validator("min_wet_low")
    @classmethod
    def validate_wetness_thresholds(
        cls,
        value: float,
        info,
    ) -> float:
        high = info.data.get("min_wet_high")
        if high is not None and value > high:
            raise ValueError(
                "min_wet_low cannot be greater than min_wet_high."
            )
        return value
