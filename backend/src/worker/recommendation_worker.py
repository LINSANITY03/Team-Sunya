"""
Controls the recommendation job workflow.

Workflow:
1. Load the recommendation job.
2. Preprocess the collected datasets.
3. Build the site and farmer input profiles.
4. Generate crop rotation recommendations.
"""

from concurrent.futures import ThreadPoolExecutor
import logging
import math
import datetime as dt

from datetime import date, datetime
from typing import Any

import pandas as pd

from schema import RecommendationRequest
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
    request_data: dict | None = None,
) -> None:
    """
    Preprocess collected datasets and generate crop rotation recommendations.
    """

    logger.info(
        "Starting recommendation job %s",
        recommendation_id,
    )

    with SessionLocal() as db:

        # 1. Retrieve job information.
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

        # 2. Ensure external data collection is complete.
        if job.status == "PENDING":
            sources = {
                "NASA_POWER": fetch_nasa_power,
                "ELEVATION": fetch_elevation,
                "SOILGRIDS": fetch_soil,
                "MODIS": fetch_modis,
            }

            job.status = "PROCESSING"
            job.error_message = None
            db.commit()

            # process_data_source opens its own SessionLocal, so threads are safe.
            with ThreadPoolExecutor(max_workers=len(sources)) as pool:
                futures = {
                    name: pool.submit(
                        process_data_source,
                        recommendation_id,
                        name,
                        fetch_function,
                        job.latitude,
                        job.longitude,
                    )
                    for name, fetch_function in sources.items()
                }
                results = {name: f.result() for name, f in futures.items()}

            failed = [name for name, ok in results.items() if not ok]

            if failed:
                job.status = "FAILED"
                job.error_message = (
                    f"External data retrieval failed for: {failed}"
                )
                db.commit()
                return

            job.status = "DATA_READY"
            db.commit()

        # 3. Only continue when all external data is available.
        if job.status != "DATA_READY":
            logger.warning(
                "Recommendation job %s is not ready. Current status: %s",
                recommendation_id,
                job.status,
            )
            return

        try:
            # 3. Mark job as processing.
            job.status = "PROCESSING"
            job.error_message = None
            db.commit()

            # . Load request configuration.
            if request_data is None:
                request_data = job.request_data

            if not request_data:
                raise ValueError(
                    f"Missing request configuration for job {recommendation_id}."
                )

            request = RecommendationRequest.model_validate(request_data)


            logger.info(
                "Initializing recommendation configuration for job %s.",
                recommendation_id,
            )

            # 5. Initialize rotation configuration.
            cfg = RotationConfig(
                cyclic=request.cyclic,
                default_family_gap=request.default_family_gap,
                harvest_mismatch_tol_days=request.harvest_mismatch_tol_days,
                max_candidates=request.max_candidates,
                max_fallow_days=request.max_fallow_days,
                max_horizon_days=request.max_horizon_days,
                max_single_crop_days=request.max_single_crop_days,
                require_legume=request.require_legume,
                rotation_length=request.rotation_length,
                turnaround_days=request.turnaround_days,
            )

            logger.info(
                "Rotation configuration initialized. "
                "Harvest mismatch tolerance: %s",
                cfg.harvest_mismatch_tol_days,
            )

            # 6. Preprocess datasets.
            preprocessed_data = run_preprocessing(
                db=db,
                recommendation_id=recommendation_id,
                config=cfg,
            )

            logger.info(
                "Preprocessing completed successfully."
            )

            # 7. Validate preprocessed datasets.
            required_datasets = [
                "weather_data",
                "soil_data",
                "modis_data",
                "elevation_data",
                "crop_data",
                "crop_calendar",
            ]

            missing_datasets = [
                name
                for name in required_datasets
                if name not in preprocessed_data
                or preprocessed_data[name] is None
            ]

            if missing_datasets:
                raise ValueError(
                    f"Missing preprocessed datasets: {missing_datasets}"
                )

            # 8. Log dataset information.
            for dataset_name, dataframe in preprocessed_data.items():
                if hasattr(dataframe, "shape"):
                    logger.info(
                        "Dataset: %s | Rows: %d | Columns: %d",
                        dataset_name,
                        dataframe.shape[0],
                        dataframe.shape[1],
                    )

            # 9. Initialize site.
            site = Site(
                power_df=preprocessed_data["weather_data"],
                soilgrid_df=preprocessed_data["soil_data"],
                modis_df=preprocessed_data["modis_data"],
                cfg=cfg,
            )

            logger.info("Site initialized successfully.")

            # 10. Initialize field profile.
            elevation_data = preprocessed_data["elevation_data"]

            if elevation_data.empty:
                raise ValueError(
                    "Elevation dataset is empty. Cannot determine terrain."
                )

            terrain = elevation_data["terrain"].iloc[0]

            field_profile = FieldProfile(
                field_id=request.field_id,
                terrain=terrain,
                irrigation=request.irrigation,
                start_date=request.start_date,
            )

            logger.info(
                "Field profile initialized. Field ID: %s | Terrain: %s",
                field_profile.field_id,
                field_profile.terrain,
            )

            # 11. Initialize farmer priorities.
            farmer_priority = FarmerPriority(
                profit=request.profit,
                food_security=request.food_security,
                soil_health=request.soil_health,
                water_saving=request.water_saving,
                low_risk=request.low_risk,
            )

            logger.info(
                "Farmer priorities initialized: %s",
                farmer_priority,
            )

            # 12. Generate crop rotation recommendations.
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

            # 13. Save ranked rotations.
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

            # 14. Mark job as completed.
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

            # 15. Mark job as failed.
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



# def process_recommendation_job(
#     recommendation_id: str,
#     request_data: dict | None = None,
# ) -> None:
#     """
#     Process a recommendation job using already collected external data.

#     Workflow:
#         1. Retrieve recommendation job.
#         2. Verify all required external data exists.
#         3. Load request configuration.
#         4. Initialize RotationConfig.
#         5. Run preprocessing.
#         6. Generate crop rotation recommendations.
#         7. Save ranked rotations.
#         8. Mark job as completed.

#     This function does not fetch external data.
#     """

#     logger.info(
#         "Starting recommendation job %s",
#         recommendation_id,
#     )

#     required_sources = {
#         "NASA_POWER",
#         "ELEVATION",
#         "SOILGRIDS",
#         "MODIS",
#     }

#     try:

#         # --------------------------------------------------
#         # 1. Retrieve recommendation job
#         # --------------------------------------------------

#         with SessionLocal() as db:

#             job = (
#                 db.query(RecommendationJob)
#                 .filter(
#                     RecommendationJob.id == recommendation_id
#                 )
#                 .first()
#             )

#             if job is None:
#                 logger.error(
#                     "Recommendation job %s does not exist.",
#                     recommendation_id,
#                 )
#                 return

#             latitude = job.latitude
#             longitude = job.longitude

#             # Use explicitly provided request data first.
#             if request_data is None:
#                 request_data = job.request_data

#             # --------------------------------------------------
#             # 2. Retrieve external data records
#             # --------------------------------------------------

#             source_records = (
#                 db.query(RecommendationData)
#                 .filter(
#                     RecommendationData.recommendation_id
#                     == recommendation_id
#                 )
#                 .all()
#             )

#             records_by_source = {
#                 record.source: record
#                 for record in source_records
#             }

#             # --------------------------------------------------
#             # 3. Validate external data availability
#             # --------------------------------------------------

#             missing_sources = (
#                 required_sources - set(records_by_source.keys())
#             )

#             invalid_sources = []

#             for source in required_sources:

#                 if source not in records_by_source:
#                     continue

#                 record = records_by_source[source]

#                 if record.status != "SUCCESS":
#                     invalid_sources.append(
#                         f"{source} (status: {record.status})"
#                     )
#                     continue

#                 if record.data is None:
#                     invalid_sources.append(
#                         f"{source} (no stored data)"
#                     )
#                     continue

#                 if isinstance(record.data, (dict, list)) and not record.data:
#                     invalid_sources.append(
#                         f"{source} (empty data)"
#                     )

#             if missing_sources or invalid_sources:

#                 problems = []

#                 if missing_sources:
#                     problems.append(
#                         "Missing sources: "
#                         + ", ".join(sorted(missing_sources))
#                     )

#                 if invalid_sources:
#                     problems.append(
#                         "Invalid sources: "
#                         + ", ".join(invalid_sources)
#                     )

#                 error_message = "; ".join(problems)

#                 # Determine whether some source data is usable.
#                 successful_count = sum(
#                     1
#                     for source in required_sources
#                     if (
#                         source in records_by_source
#                         and records_by_source[source].status == "SUCCESS"
#                         and records_by_source[source].data is not None
#                         and not (
#                             isinstance(
#                                 records_by_source[source].data,
#                                 (dict, list),
#                             )
#                             and not records_by_source[source].data
#                         )
#                     )
#                 )

#                 job.status = (
#                     "PARTIAL_FAILED"
#                     if successful_count > 0
#                     else "FAILED"
#                 )

#                 job.error_message = error_message
#                 db.commit()

#                 logger.error(
#                     "Recommendation %s cannot proceed: %s",
#                     recommendation_id,
#                     error_message,
#                 )

#                 return

#             # --------------------------------------------------
#             # 4. Mark job as processing
#             # --------------------------------------------------

#             job.status = "PROCESSING"
#             job.error_message = None
#             db.commit()

#             logger.info(
#                 "All required external data is available for %s.",
#                 recommendation_id,
#             )

#         # --------------------------------------------------
#         # 5. Validate request configuration
#         # --------------------------------------------------

#         if not request_data:
#             raise ValueError(
#                 f"Missing request configuration for job "
#                 f"{recommendation_id}."
#             )

#         request = RecommendationRequest.model_validate(
#             request_data
#         )

#         # --------------------------------------------------
#         # 6. Initialize RotationConfig
#         # --------------------------------------------------

#         cfg = RotationConfig(
#             cyclic=request.cyclic,
#             default_family_gap=request.default_family_gap,
#             harvest_mismatch_tol_days=request.harvest_mismatch_tol_days,
#             max_candidates=request.max_candidates,
#             max_fallow_days=request.max_fallow_days,
#             max_horizon_days=request.max_horizon_days,
#             max_single_crop_days=request.max_single_crop_days,
#             require_legume=request.require_legume,
#             rotation_length=request.rotation_length,
#             turnaround_days=request.turnaround_days,
#         )

#         logger.info(
#             "RotationConfig initialized for recommendation %s.",
#             recommendation_id,
#         )

#         # --------------------------------------------------
#         # 7. Run preprocessing
#         # --------------------------------------------------

#         with SessionLocal() as db:

#             preprocessed_data = run_preprocessing(
#                 db=db,
#                 recommendation_id=recommendation_id,
#                 config=cfg,
#             )

#             logger.info(
#                 "Preprocessing completed. Datasets: %d",
#                 len(preprocessed_data),
#             )

#             # --------------------------------------------------
#             # 8. Validate preprocessed datasets
#             # --------------------------------------------------

#             required_datasets = [
#                 "weather_data",
#                 "soil_data",
#                 "modis_data",
#                 "elevation_data",
#                 "crop_data",
#                 "crop_calendar",
#             ]

#             missing_datasets = [
#                 name
#                 for name in required_datasets
#                 if name not in preprocessed_data
#                 or preprocessed_data[name] is None
#             ]

#             if missing_datasets:
#                 raise ValueError(
#                     f"Missing preprocessed datasets: "
#                     f"{missing_datasets}"
#                 )

#             # Check elevation.
#             elevation_data = preprocessed_data["elevation_data"]

#             if elevation_data.empty:
#                 raise ValueError(
#                     "Elevation dataset is empty. "
#                     "Cannot determine terrain."
#                 )

#             # --------------------------------------------------
#             # 9. Initialize Site
#             # --------------------------------------------------

#             site = Site(
#                 power_df=preprocessed_data["weather_data"],
#                 soilgrid_df=preprocessed_data["soil_data"],
#                 modis_df=preprocessed_data["modis_data"],
#                 cfg=cfg,
#             )

#             logger.info("Site initialized successfully.")

#             # --------------------------------------------------
#             # 10. Initialize FieldProfile
#             # --------------------------------------------------

#             terrain = elevation_data["terrain"].iloc[0]

#             field_profile = FieldProfile(
#                 field_id=request.field_id,
#                 terrain=terrain,
#                 irrigation=request.irrigation,
#                 start_date=request.start_date,
#             )

#             # --------------------------------------------------
#             # 11. Initialize FarmerPriority
#             # --------------------------------------------------

#             farmer_priority = FarmerPriority(
#                 profit=request.profit,
#                 food_security=request.food_security,
#                 soil_health=request.soil_health,
#                 water_saving=request.water_saving,
#                 low_risk=request.low_risk,
#             )

#             logger.info(
#                 "Farmer priorities initialized: %s",
#                 farmer_priority,
#             )

#             # --------------------------------------------------
#             # 12. Generate crop rotation recommendations
#             # --------------------------------------------------

#             recommendation_result = run_rotation_strategy(
#                 preprocessed_data["crop_data"],
#                 preprocessed_data["crop_calendar"],
#                 site,
#                 field_profile,
#                 farmer_priority,
#                 cfg,
#             )

#             logger.info(
#                 "Crop rotation recommendations generated."
#             )

#             # --------------------------------------------------
#             # 13. Save ranked rotations
#             # --------------------------------------------------

#             saved_rotations = save_rotations(
#                 db=db,
#                 recommendation_id=recommendation_id,
#                 results=recommendation_result,
#             )

#             db.commit()

#             logger.info(
#                 "Saved %d crop rotation recommendations for %s.",
#                 len(saved_rotations),
#                 recommendation_id,
#             )

#         # --------------------------------------------------
#         # 14. Mark recommendation as completed
#         # --------------------------------------------------

#         update_job_status(
#             recommendation_id=recommendation_id,
#             status="COMPLETED",
#             error_message=None,
#         )

#         logger.info(
#             "Recommendation job %s completed successfully.",
#             recommendation_id,
#         )

#     except Exception as exc:

#         logger.exception(
#             "Recommendation processing failed for job %s.",
#             recommendation_id,
#         )

#         try:
#             update_job_status(
#                 recommendation_id=recommendation_id,
#                 status="FAILED",
#                 error_message=str(exc),
#             )

#         except Exception:
#             logger.exception(
#                 "Could not update failure status for job %s.",
#                 recommendation_id,
#             )

#         raise
