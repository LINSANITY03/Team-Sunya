from fastapi import APIRouter, HTTPException, logger, status, BackgroundTasks, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session
from uuid import UUID

from database.models import RecommendationData, RecommendationJob
from database.connection import get_db

from services.location_service import is_inside_nepal
from worker.recommendation_worker import process_recommendation_job
from repository.crop_recommendation_repository import get_rotations

import logging

logger = logging.getLogger(__name__)

class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

router = APIRouter(prefix="/rotations", tags=["Rotations"])

@router.post("/recommend", status_code=status.HTTP_202_ACCEPTED,)
def recommend_rotations(
    location: Location,
    background_tasks: BackgroundTasks,
    d_recommendation_id: UUID | None = None, 
    db: Session = Depends(get_db),
    ):
    """
        Validate coordinates, create a recommendation job,
        and schedule external data retrieval in the background.
    """

    if d_recommendation_id:
        data_recommendation_id = str(d_recommendation_id)

        logger.info(
            "Reusing external data from recommendation %s",
            data_recommendation_id,
        )
        background_tasks.add_task(
            process_recommendation_job,
            data_recommendation_id,
        )
        return {
            "status": "accepted",
            "message": "Recommendation request accepted for processing.",
            "recommendation_id": data_recommendation_id,
        }

    latitude = location.latitude
    longitude = location.longitude

    # 1. Validate Nepal boundary
    if not is_inside_nepal(latitude, longitude):
        raise HTTPException(
            status_code=400,
            detail="The selected location is outside Nepal."
        )

    # 2. Create recommendation job.
    job = RecommendationJob(
        latitude=latitude,
        longitude=longitude,
        request_data=location.model_dump(),
        status="PENDING",
    )

    db.add(job)

    # Generate the UUID and persist the job before scheduling work.
    db.flush()
    
    # 3. Create pending records for each external data source.
    sources = [
        "NASA_POWER",
        "ELEVATION",
        "SOILGRIDS",
        "MODIS",
    ]

    for source in sources:
        db.add(
            RecommendationData(
                recommendation_id=job.id,
                source=source,
                status="PENDING",
            )
        )

    # 4. Commit before starting background processing.
    db.commit()
    db.refresh(job)
    
    recommendation_id = job.id

    # 5. Schedule background processing.
    background_tasks.add_task(
        process_recommendation_job,
        recommendation_id,
    )

    # 6. Return immediately.
    return {
        "status": "accepted",
        "message": "Recommendation request accepted for processing.",
        "recommendation_id": recommendation_id,
        "job_status": job.status,
    }

@router.get(
    "/{recommendation_id}",
    status_code=status.HTTP_200_OK,
)
def get_recommendation_status(
    recommendation_id: str,
    db: Session = Depends(get_db),
):
    """
        Retrieve recommendation job status, external data-source
        statuses, and generated crop rotation recommendations.
    """

    # 1. Find recommendation job.
    job = (
        db.query(RecommendationJob)
        .filter(
            RecommendationJob.id == recommendation_id
        )
        .first()
    )

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation job not found.",
        )

    # 2. Retrieve individual data-source records.
    data_sources = (
        db.query(RecommendationData)
        .filter(
            RecommendationData.recommendation_id
            == recommendation_id
        )
        .all()
    )

    # 3. Format source statuses.
    sources = {}

    for source in data_sources:
        sources[source.source] = {
            "status": source.status,
            "error_message": source.error_message,
            "data_available": source.data is not None,
        }

    # 4. Retrieve saved crop rotations.
    rotations = get_rotations(
        db=db,
        recommendation_id=recommendation_id,
    )

    # 5. Format rotations for the frontend.
    results = [
        {
            "rank": rotation.rank,
            "score": rotation.score,
            "sequence": rotation.sequence,
            "rotation_data": rotation.rotation_data,
        }
        for rotation in rotations
    ]

    # 5. Return job information.
    return {
        "recommendation_id": job.id,
        "status": job.status,
        "location": {
            "latitude": job.latitude,
            "longitude": job.longitude,
        },
        "data_sources": sources,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "results": results,
    }


@router.get("/", status_code=status.HTTP_200_OK)
def get_all_recommendation_jobs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return paginated recommendation jobs and their results."""

    offset = (page - 1) * limit

    # Total number of recommendation jobs.
    total = (
        db.query(func.count(RecommendationJob.id))
        .scalar()
    ) or 0

    # Retrieve jobs, newest first.
    jobs = (
        db.query(RecommendationJob)
        .order_by(RecommendationJob.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    if not jobs:
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": 0 if total == 0 else (total + limit - 1) // limit,
            "returned": 0,
            "recommendations": [],
        }

    job_ids = [job.id for job in jobs]

    # Retrieve source statuses without loading large JSON datasets.
    source_rows = (
        db.query(
            RecommendationData.recommendation_id,
            RecommendationData.source,
            RecommendationData.status,
            RecommendationData.error_message,
            RecommendationData.data.is_not(None).label("data_available"),
        )
        .filter(
            RecommendationData.recommendation_id.in_(job_ids)
        )
        .all()
    )

    sources_by_job = {}

    for row in source_rows:
        sources_by_job.setdefault(
            row.recommendation_id, {}
        )[row.source] = {
            "status": row.status,
            "data_available": row.data_available,
            "error_message": row.error_message,
        }

    recommendations = []

    for job in jobs:
        recommendations.append({
            "recommendation_id": job.id,
            "status": job.status,
            "location": {
                "latitude": job.latitude,
                "longitude": job.longitude,
            },
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "error_message": job.error_message,
            "data_sources": sources_by_job.get(job.id, {}),
            "results": job.result_data,
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
        "returned": len(recommendations),
        "recommendations": recommendations,
    }

