"""
Controls the recommendation job workflow.

Workflow:
1. Load the recommendation job.
2. Preprocess the collected datasets.
3. Build the site and farmer input profiles.
4. Generate crop rotation recommendations.
"""

import logging
import math
import datetime as dt

from datetime import date, datetime
from typing import Any

import pandas as pd

from database.connection import SessionLocal
from database.models import RecommendationJob, RecommendationData

from engine.farmer_priorities import FarmerPriority
from engine.field_profile import FieldProfile
from engine.site import Site
from engine.rotation_strategy import run_rotation_strategy
from engine.config import RotationConfig

from services.preprocessing_service import run_preprocessing
from services.nasa_power_service import NASAPowerService
from services.terrain_service import TerrainService
from services.soil_service import SoilService
from services.modis_service import MODISService

from repository.crop_recommendation_repository import save_rotations

logger = logging.getLogger(__name__)

DEFAULT_FIELD_START_DATE = dt.date(2026, 3, 1)

# --------------------------------------------------
# JSON serialization helpers
# --------------------------------------------------

def make_json_serializable(value: Any) -> Any:
    """
    Convert Pandas, NumPy, and Python values into JSON-compatible values.
    """

    if value is None:
        return None

    if isinstance(value, dict):
        return {
            str(key): make_json_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [make_json_serializable(item) for item in value]

    if isinstance(value, pd.DataFrame):
        return make_json_serializable(
            value.to_dict(orient="records")
        )

    if isinstance(value, pd.Series):
        return make_json_serializable(value.to_dict())

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    # Convert NumPy scalar values to native Python values.
    if hasattr(value, "item") and callable(value.item):
        try:
            value = value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, float) and not math.isfinite(value):
        return None

    # Handle Pandas missing values.
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


# --------------------------------------------------
# Database update helpers
# --------------------------------------------------

def update_source_status(
    recommendation_id: str,
    source: str,
    status: str,
    data: dict | list | None = None,
    error_message: str | None = None,
) -> None:
    """
    Update the status and result of an individual data source.
    """

    with SessionLocal() as db:
        source_record = (
            db.query(RecommendationData)
            .filter(
                RecommendationData.recommendation_id
                == recommendation_id,
                RecommendationData.source == source,
            )
            .first()
        )

        if source_record is None:
            raise ValueError(
                f"Source record '{source}' not found for job "
                f"{recommendation_id}."
            )

        source_record.status = status
        source_record.data = (
            make_json_serializable(data)
            if data is not None
            else None
        )
        source_record.error_message = error_message

        db.commit()


def update_job_status(
    recommendation_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Update the overall recommendation job status."""

    with SessionLocal() as db:
        job = (
            db.query(RecommendationJob)
            .filter(
                RecommendationJob.id == recommendation_id
            )
            .first()
        )

        if job is None:
            raise ValueError(
                f"Recommendation job {recommendation_id} not found."
            )

        job.status = status
        job.error_message = error_message

        db.commit()


# --------------------------------------------------
# External data retrieval
# --------------------------------------------------

def fetch_nasa_power(
    latitude: float,
    longitude: float,
) -> dict:
    """Retrieve NASA POWER weather data."""

    df = NASAPowerService.fetch_daily_data(
        latitude=latitude,
        longitude=longitude,
    )

    return {
        "start_date": NASAPowerService.START_DATE,
        "end_date": NASAPowerService.END_DATE,
        "total_records": len(df),
        "data": make_json_serializable(df),
    }


def fetch_elevation(
    latitude: float,
    longitude: float,
) -> dict:
    """Retrieve elevation and terrain classification."""

    result = TerrainService.get_terrain_elevation(
        latitude=latitude,
        longitude=longitude,
    )

    return make_json_serializable(result)


def fetch_soil(
    latitude: float,
    longitude: float,
) -> dict:
    """Retrieve SoilGrids soil properties."""

    df = SoilService.get_soil_properties(
        latitude=latitude,
        longitude=longitude,
    )

    return {
        "total_records": len(df),
        "data": make_json_serializable(df),
    }


def fetch_modis(latitude: float, longitude: float) -> dict:
    """Fetch MODIS vegetation-index data for the recommendation location."""

    service = MODISService()

    result = service.fetch_data(
        latitude=latitude,
        longitude=longitude,
    )

    if result["total_observations"] == 0:
        raise RuntimeError("MODIS returned no observations.")

    if result["valid_observations"] == 0:
        raise RuntimeError(
            "MODIS returned observations, but none passed the quality filter."
        )

    return result

# --------------------------------------------------
# Individual source processing
# --------------------------------------------------

def process_data_source(
    recommendation_id: str,
    source: str,
    fetch_function,
    latitude: float,
    longitude: float,
) -> bool:
    """
    Fetch one external data source and persist its result.

    Returns True when successful, otherwise False.
    """

    try:
        # Mark source as processing.
        update_source_status(
            recommendation_id=recommendation_id,
            source=source,
            status="PROCESSING",
        )

        logger.info(
            "Fetching %s for recommendation %s",
            source,
            recommendation_id,
        )

        # Retrieve external data.
        result = fetch_function(
            latitude=latitude,
            longitude=longitude,
        )

        # Save successful response.
        update_source_status(
            recommendation_id=recommendation_id,
            source=source,
            status="SUCCESS",
            data=result,
        )

        logger.info(
            "%s retrieval successful for recommendation %s",
            source,
            recommendation_id,
        )

        return True

    except Exception as exc:
        error_message = str(exc)

        logger.exception(
            "%s retrieval failed for recommendation %s",
            source,
            recommendation_id,
        )

        try:
            update_source_status(
                recommendation_id=recommendation_id,
                source=source,
                status="FAILED",
                error_message=error_message,
            )
        except Exception:
            logger.exception(
                "Could not save failure status for %s, job %s",
                source,
                recommendation_id,
            )

        return False


# --------------------------------------------------
# Main background worker
# --------------------------------------------------

def process_recommendation_job(
    recommendation_id: str,
) -> None:
    """
        Preprocess collected datasets and generate crop rotation recommendations.
    """

    logger.info(
        "Starting recommendation job %s",
        recommendation_id,
    )

    # 1. Retrieve job information.
    with SessionLocal() as db:
        job = (
            db.query(RecommendationJob)
            .filter(
                RecommendationJob.id == recommendation_id
            )
            .first()
        )

        if job is None:
            logger.error(
                "Recommendation job %s does not exist.",
                recommendation_id,
            )
            return

        if job.status != "DATA_READY":
            logger.warning(
                "Recommendation job %s is not ready. Current status: %s",
                recommendation_id,
                job.status,
            )
            return
        
        try: 
            # 2. Mark job as processing.
            job.status = "PROCESSING"
            job.error_message = None
            db.commit()

            # 3. Initialize rotation configuration.
            cfg = RotationConfig()

            logger.info(
                "Harvest mismatch tolerance: %s",
                cfg.harvest_mismatch_tol_days,
            )

            # 4. Preprocess datasets.
            preprocessed_data = run_preprocessing(
                db=db,
                recommendation_id=recommendation_id,
                config=cfg,
            )

            logger.info(
                "Preprocessing completed successfully."
            )

            # 5. Log dataset information.
            for dataset_name, dataframe in preprocessed_data.items():
                logger.info(
                    "Dataset: %s | Rows: %d | Columns: %d",
                    dataset_name,
                    len(dataframe),
                    len(dataframe.columns),
                )

            # 5. Initialize site.
            site = Site(
                power_df=preprocessed_data["weather_data"],
                soilgrid_df=preprocessed_data["soil_data"],
                modis_df=preprocessed_data["modis_data"],
                cfg=cfg,
            )

            # 6. Initialize field profile.
            field_profile = FieldProfile(
                field_id=(
                    f"{recommendation_id}-"
                    f"{job.latitude}-{job.longitude}"
                ),
                terrain=preprocessed_data[
                    "elevation_data"
                ]["terrain"].iloc[0],
                irrigation=False,
                start_date=DEFAULT_FIELD_START_DATE,
            )

            # 6. Initialize farmer priorities.
            farmer_priority = FarmerPriority()

            # 7. Generate crop rotation recommendations.
            recommendation_result = run_rotation_strategy(
                preprocessed_data["crop_data"],
                preprocessed_data["crop_calendar"],
                site,
                field_profile,
                farmer_priority,
                cfg,
            )

            logger.info(
                "Crop rotation recommendations generated successfully."
            )

            logger.info(
                "Recommendation result: %s",
                recommendation_result,
            )
            # 8. Save all ranked rotations.
            saved_rotations = save_rotations(
                db=db,
                recommendation_id=recommendation_id,
                results=recommendation_result,
            )
            logger.info(
                "Saved %d crop rotation recommendations for job %s.",
                len(saved_rotations),
                recommendation_id,
            )

            # 9. Mark job as completed.
            job.status = "COMPLETED"
            job.error_message = None

            db.commit()

            logger.info(
                "Recommendation job %s completed successfully.",
                recommendation_id,
            )

        except Exception as exc:
            db.rollback()

            logger.exception(
                "Recommendation processing failed for job %s.",
                recommendation_id,
            )
            # Mark the job as failed.
            try:
                failed_job = (
                    db.query(RecommendationJob)
                    .filter(
                        RecommendationJob.id == recommendation_id
                    )
                    .first()
                )

                if failed_job is not None:
                    failed_job.status = "FAILED"
                    failed_job.error_message = str(exc)
                    db.commit()

            except Exception:
                db.rollback()
                logger.exception(
                    "Could not update failure status for job %s.",
                    recommendation_id,
                )

            raise

    logger.info(
        "Recommendation job %s completed.",
        recommendation_id,
    )