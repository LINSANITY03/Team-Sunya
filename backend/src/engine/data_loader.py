"""
    Retrieves and converts data.
"""
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from repository.recommendation_data_repository import (
    RecommendationDataRepository,
)


BASE_DIR = Path(__file__).resolve().parents[2]
CROP_DIR = BASE_DIR / "data" / "Crop" / "cleaned"
CROP_PATH = (CROP_DIR / "combined_crop_table.csv")
CROP_CALENDAR_PATH = CROP_DIR / "crop_calender.csv"


ATTR_RENAME = {
    "Crop Name": "crop",
    "Botanical Species Name": "species",
    "Botanical Family": "family",
    "Primary Agronomic Function": "function",
    "Terai": "terai",
    "Hill": "hill",
    "Mountain": "mountain",
    "Rooting depth (m)": "rooting_depth_m",
    "Category": "category",
    "Optimal pH Min": "ph_opt_min",
    "Optimal pH Max": "ph_opt_max",
    "Absolute pH Min": "ph_abs_min",
    "Absolute pH Max": "ph_abs_max",
    "Agronomic Notes": "agronomic_notes",
}


class DataLoader:
    """Load static crop datasets and job-specific external data."""

    def __init__(
        self,
        db: Session,
        recommendation_id: str,
    ) -> None:
        self.recommendation_id = recommendation_id

        self.recommendation_repository = (
            RecommendationDataRepository(db)
        )

    @staticmethod
    def _load_csv(path: Path, dataset_name: str) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(
                f"{dataset_name} not found: {path}"
            )

        return pd.read_csv(path)
    
    @classmethod
    def load_crop_data(cls) -> pd.DataFrame:
        """Load and normalize crop characteristics."""

        df = cls._load_csv(CROP_PATH, "Crop dataset")

        df = df.rename(columns=ATTR_RENAME)

        if "crop" not in df.columns:
            raise ValueError(
                "Crop dataset must contain a Crop Name column."
            )

        return df
    
    @classmethod
    def load_crop_calendar(cls) -> pd.DataFrame:
        """Load the crop sowing and harvesting calendar."""

        df = cls._load_csv(
            CROP_CALENDAR_PATH,
            "Crop calendar",
        )

        required_columns = {
            "crop",
            "aez",
            "sow_early_month",
            "sow_early_day",
            "harv_early_month",
            "harv_early_day",
            "gp_value",
        }
        missing = required_columns - set(df.columns)

        if missing:
            raise ValueError(
                f"Crop calendar is missing columns: {sorted(missing)}"
            )

        return df

    @staticmethod
    def _records_to_dataframe(
        payload: dict,
        source_name: str,
    ) -> pd.DataFrame:
        """Extract the nested records from a worker payload."""

        if not isinstance(payload, dict):
            raise TypeError(
                f"{source_name} payload must be a dictionary."
            )

        records = payload.get("data")

        if not isinstance(records, list):
            raise ValueError(
                f"{source_name} payload must contain a list under 'data'."
            )

        return pd.DataFrame(records)

    @classmethod
    def load_weather_data(cls, payload: dict) -> pd.DataFrame:
        """Convert NASA POWER payload into a DataFrame."""

        return cls._records_to_dataframe(
            payload,
            "NASA_POWER",
        )

    @classmethod
    def load_soil_data(cls, payload: dict) -> pd.DataFrame:
        """Convert SoilGrids payload into a DataFrame."""

        return cls._records_to_dataframe(
            payload,
            "SOILGRIDS",
        )

    @staticmethod
    def load_elevation_data(payload: dict) -> pd.DataFrame:
        """Convert elevation payload into a one-row DataFrame."""

        if not isinstance(payload, dict):
            raise TypeError("ELEVATION payload must be a dictionary.")

        return pd.DataFrame([payload])

    @classmethod
    def load_modis_data(cls, payload: dict) -> pd.DataFrame:
        """Convert MODIS payload into a DataFrame."""

        return cls._records_to_dataframe(
            payload,
            "MODIS",
        )

    def load(self) -> dict[str, pd.DataFrame]:
        """Load all datasets required by the recommendation engine."""

        sources = self.recommendation_repository.get_successful_sources(
            self.recommendation_id
        )

        return {
            "crop_data": self.load_crop_data(),
            "crop_calendar": self.load_crop_calendar(),
            "weather_data": self.load_weather_data(
                sources["NASA_POWER"]
            ),
            "soil_data": self.load_soil_data(
                sources["SOILGRIDS"]
            ),
            "elevation_data": self.load_elevation_data(
                sources["ELEVATION"]
            ),
            "modis_data": self.load_modis_data(
                sources["MODIS"]
            ),
        }
