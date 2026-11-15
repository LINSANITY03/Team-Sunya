
"""
Repository for storing and retrieving crop rotation recommendations.
"""

from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd

from sqlalchemy.orm import Session

from database.models import CropRotationRecommendation


# --------------------------------------------------
# Serialization
# --------------------------------------------------

def make_json_serializable(value: Any) -> Any:
    """Convert Python, Pandas, and NumPy values into JSON-compatible values."""

    if value is None:
        return None

    if isinstance(value, pd.DataFrame):
        return make_json_serializable(
            value.to_dict(orient="records")
        )

    if isinstance(value, pd.Series):
        return make_json_serializable(value.to_dict())

    if isinstance(value, dict):
        return {
            str(key): make_json_serializable(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            make_json_serializable(item)
            for item in value
        ]

    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()

    if isinstance(value, np.generic):
        return make_json_serializable(value.item())

    if isinstance(value, float) and not np.isfinite(value):
        return None

    return value


# --------------------------------------------------
# Normalize recommendation results
# --------------------------------------------------

def normalize_rotation_results(
    results: Any,
) -> list[dict]:
    """
    Normalize rotation results into a list of dictionaries.

    Supported inputs:
        - list[dict]
        - pandas DataFrame
        - single rotation dictionary
        - dictionary containing 'ranked' and/or 'top'
    """

    if results is None:
        return []

    # Handle the result structure returned by the strategy.
    if isinstance(results, dict):
        if "ranked" in results:
            results = results["ranked"]
        elif "top" in results:
            results = results["top"]
        elif "rank" in results:
            results = [results]
        else:
            raise ValueError(
                "Unrecognized recommendation result dictionary."
            )

    # Convert DataFrame into records.
    if isinstance(results, pd.DataFrame):
        rotations = results.to_dict(orient="records")

    elif isinstance(results, list):
        rotations = results

    else:
        raise TypeError(
            "Rotation results must be a list, DataFrame, "
            "or dictionary."
        )

    normalized = []

    for index, rotation in enumerate(rotations, start=1):
        if not isinstance(rotation, dict):
            raise TypeError(
                f"Rotation at position {index} must be a dictionary."
            )

        rotation = make_json_serializable(rotation)

        rank = rotation.get("rank", index)
        score = rotation.get("score", rotation.get("total_score"))
        sequence = rotation.get("sequence")

        if rank is None or score is None or sequence is None:
            raise ValueError(
                f"Rotation at position {index} must contain "
                "'rank', 'score' (or 'total_score'), and 'sequence'."
            )

        normalized.append({
            "rank": int(rank),
            "score": float(score),
            "sequence": str(sequence),
            "rotation_data": rotation,
        })

    return normalized


# --------------------------------------------------
# Save recommendations
# --------------------------------------------------

def save_rotations(
    db: Session,
    recommendation_id: str,
    results: Any,
) -> list[CropRotationRecommendation]:
    """
    Save ranked crop rotation recommendations.

    Existing rotations for the same job are replaced,
    making repeated processing safe from duplicate results.

    The caller is responsible for committing the transaction.
    """

    rotations = normalize_rotation_results(results)

    if not rotations:
        raise ValueError(
            "Cannot save an empty set of crop rotations."
        )

    # Remove previous results for this recommendation job.
    (
        db.query(CropRotationRecommendation)
        .filter(
            CropRotationRecommendation.recommendation_id
            == recommendation_id
        )
        .delete(synchronize_session=False)
    )

    # Create database records.
    records = [
        CropRotationRecommendation(
            recommendation_id=recommendation_id,
            rank=rotation["rank"],
            score=rotation["score"],
            sequence=rotation["sequence"],
            rotation_data=rotation["rotation_data"],
        )
        for rotation in rotations
    ]

    db.add_all(records)
    db.flush()

    return records


# --------------------------------------------------
# Retrieve recommendations
# --------------------------------------------------

def get_rotations(
    db: Session,
    recommendation_id: str,
) -> list[CropRotationRecommendation]:
    """Retrieve all rotations for a job, ordered by rank."""

    return (
        db.query(CropRotationRecommendation)
        .filter(
            CropRotationRecommendation.recommendation_id
            == recommendation_id
        )
        .order_by(
            CropRotationRecommendation.rank.asc()
        )
        .all()
    )


def get_top_rotations(
    db: Session,
    recommendation_id: str,
    limit: int = 5,
) -> list[CropRotationRecommendation]:
    """Retrieve the top K rotations for a job."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    return (
        db.query(CropRotationRecommendation)
        .filter(
            CropRotationRecommendation.recommendation_id
            == recommendation_id
        )
        .order_by(
            CropRotationRecommendation.rank.asc()
        )
        .limit(limit)
        .all()
    )
