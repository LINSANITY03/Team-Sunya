
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class RecommendationJob(Base):
    """
    Stores the overall status and results of a crop rotation
    recommendation request.
    """

    __tablename__ = "recommendation_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'DATA_READY', "
            "'COMPLETED', 'PARTIAL_FAILED', 'FAILED')",
            name="check_recommendation_job_status",
        ),
        Index("ix_recommendation_jobs_status", "status"),
        Index("ix_recommendation_jobs_created_at", "created_at"),
    )

    # Unique recommendation ID generated using UUID v4.
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Geographic coordinates.
    latitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    longitude: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Original recommendation request.
    # Stores location, farmer priorities, constraints, etc.
    request_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    # Overall recommendation processing status.
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    # Final crop rotation recommendations.
    result_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Overall error message, if the job fails.
    error_message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    # Record creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Last update timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationship with external data-source records.
    data_sources: Mapped[list["RecommendationData"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
    )

    # Relationship with generated crop rotation recommendations.
    rotations: Mapped[list["CropRotationRecommendation"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CropRotationRecommendation.rank",
    )


class RecommendationData(Base):
    """
    Stores the processing status and retrieved data
    for each external data source.
    """

    __tablename__ = "recommendation_data"

    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'PROCESSING', 'SUCCESS', 'FAILED')",
            name="check_recommendation_data_status",
        ),
        UniqueConstraint(
            "recommendation_id",
            "source",
            name="uq_recommendation_source",
        ),
        Index(
            "ix_recommendation_data_source",
            "source",
        ),
    )

    # Auto-incrementing record ID.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Parent recommendation job ID.
    recommendation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "recommendation_jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # External data source.
    # Examples: NASA_POWER, ELEVATION, SOILGRIDS.
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    # Individual data-source processing status.
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    # Retrieved response data.
    data: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
    )

    # Error details if data retrieval fails.
    error_message: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )

    # Record creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Last update timestamp.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    # Relationship with the parent recommendation job.
    job: Mapped["RecommendationJob"] = relationship(
        back_populates="data_sources",
    )


class CropRotationRecommendation(Base):
    """
    Stores an individual ranked crop rotation
    generated for a recommendation job.
    """

    __tablename__ = "crop_rotation_recommendations"

    __table_args__ = (
        UniqueConstraint(
            "recommendation_id",
            "rank",
            name="uq_recommendation_rotation_rank",
        ),
        CheckConstraint(
            "rank >= 1",
            name="check_rotation_rank",
        ),
        Index(
            "ix_crop_rotation_recommendations_score",
            "score",
        ),
    )

    # Unique rotation record ID.
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Parent recommendation job.
    recommendation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "recommendation_jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    # Position in the ranked recommendation results.
    rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Overall recommendation score.
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    # Human-readable crop sequence.
    sequence: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    # Complete rotation information.
    # Includes crops, sowing dates, harvest dates,
    # water fit, fallow days, and other metrics.
    rotation_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
    )

    # Record creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    # Relationship with parent recommendation job.
    job: Mapped["RecommendationJob"] = relationship(
        back_populates="rotations",
    )
