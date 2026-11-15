"""
    Connects loading and preprocessing.
"""



import logging
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from engine.config import RotationConfig
from engine.data_loader import DataLoader
from engine.preprocessing import Preprocessor


logger = logging.getLogger(__name__)


def run_preprocessing(
    db: Session,
    recommendation_id: str,
    config: RotationConfig,
) -> dict[str, pd.DataFrame]:
    """
    Load and preprocess all datasets for a recommendation job.

    Args:
        db: Active SQLAlchemy database session.
        recommendation_id: ID of the recommendation job.
        config: Configuration used by the preprocessor.

    Returns:
        Dictionary containing all preprocessed DataFrames.

    Raises:
        Exception: If data loading or preprocessing fails.
    """

    logger.info(
        "Starting preprocessing for recommendation %s",
        recommendation_id,
    )

    try:
        # 1. Load static crop data and collected external data.
        data_loader = DataLoader(
            db=db,
            recommendation_id=recommendation_id,
        )

        datasets = data_loader.load()

        # 2. Verify that all expected datasets are present.
        expected_datasets = {
            "crop_data",
            "crop_calendar",
            "weather_data",
            "soil_data",
            "elevation_data",
            "modis_data",
        }

        missing_datasets = expected_datasets - set(datasets.keys())

        if missing_datasets:
            raise ValueError(
                "Missing datasets: "
                f"{sorted(missing_datasets)}"
            )

        # 3. Run preprocessing.
        preprocessor = Preprocessor(
            datasets=datasets,
            config=config,
        )

        processed_data = preprocessor.preprocess()

        # 4. Validate the returned datasets.
        for name in expected_datasets:
            if name not in processed_data:
                raise ValueError(
                    f"Preprocessing did not return '{name}'."
                )

            if not isinstance(processed_data[name], pd.DataFrame):
                raise TypeError(
                    f"Preprocessed '{name}' must be a DataFrame."
                )

            if processed_data[name].empty:
                logger.warning(
                    "Preprocessed dataset '%s' is empty for %s",
                    name,
                    recommendation_id,
                )

        logger.info(
            "Preprocessing completed for recommendation %s",
            recommendation_id,
        )

        return processed_data

    except Exception:
        logger.exception(
            "Preprocessing failed for recommendation %s",
            recommendation_id,
        )
        raise

