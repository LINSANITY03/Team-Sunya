
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

MODIS_START_DATE = os.getenv("MODIS_START_DATE")
MODIS_END_DATE = os.getenv("MODIS_END_DATE")

PRODUCT = os.getenv("PRODUCT")

REQUESTED_LAYERS = [
    "_250m_16_days_NDVI",
    "_250m_16_days_EVI",
    "_250m_16_days_pixel_reliability",
    "_250m_16_days_VI_Quality",
]

APPEEARS_BASE_URL = (
    "https://appeears.earthdatacloud.nasa.gov/api"
)

POLL_SECONDS = 300 # based on observation it takes 10-20min usually for AppEEARS data to be ready
TASK_TIMEOUT_MINUTES = 180

NDVI_COLUMN = "MOD13Q1_061__250m_16_days_NDVI"
EVI_COLUMN = "MOD13Q1_061__250m_16_days_EVI"
QA_COLUMN = "MOD13Q1_061__250m_16_days_pixel_reliability"

BASE_DIR = Path(__file__).resolve().parents[2]
MODIS_DATA_DIR = BASE_DIR / "data" / "MODIS"


class MODISService:
    """Fetch and process MODIS vegetation-index data using AppEEARS."""

    def __init__(self) -> None:
        self.username = os.getenv("EARTHDATA_USERNAME")
        self.password = os.getenv("EARTHDATA_PASSWORD")

        if not self.username or not self.password:
            raise RuntimeError(
                "EARTHDATA_USERNAME and EARTHDATA_PASSWORD "
                "must be configured in the .env file."
            )

        self.session = requests.Session()

    def _authenticate(self) -> None:
        """Authenticate with NASA AppEEARS."""

        response = self.session.post(
            f"{APPEEARS_BASE_URL}/login",
            auth=(self.username, self.password),
            timeout=60,
        )
        response.raise_for_status()

        token = response.json().get("token")

        if not token:
            raise RuntimeError(
                "AppEEARS authentication response did not "
                "contain an access token."
            )

        self.session.headers.update({
            "Authorization": f"Bearer {token}"
        })

        logger.info("Authenticated with NASA AppEEARS.")

    @staticmethod
    def _format_date(date_string: str) -> str:
        """Convert YYYY-MM-DD into AppEEARS MM-DD-YYYY format."""

        return datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).strftime("%m-%d-%Y")

    def _submit_task(
        self,
        latitude: float,
        longitude: float,
    ) -> str:
        """Submit a MODIS point extraction task."""

        start_date = self._format_date(MODIS_START_DATE)
        end_date = self._format_date(MODIS_END_DATE)

        task_name = (
            f"MOD13Q1_{latitude:.5f}_{longitude:.5f}_"
            f"{MODIS_START_DATE}_to_{MODIS_END_DATE}"
        )

        task_payload = {
            "task_type": "point",
            "task_name": task_name,
            "params": {
                "dates": [
                    {
                        "startDate": start_date,
                        "endDate": end_date,
                    }
                ],
                "layers": [
                    {
                        "product": PRODUCT,
                        "layer": layer,
                    }
                    for layer in REQUESTED_LAYERS
                ],
                "coordinates": [
                    {
                        "id": "study_point",
                        "longitude": longitude,
                        "latitude": latitude,
                    }
                ],
            },
        }

        response = self.session.post(
            f"{APPEEARS_BASE_URL}/task",
            json=task_payload,
            timeout=60,
        )
        response.raise_for_status()

        task_id = response.json().get("task_id")

        if not task_id:
            raise RuntimeError(
                "AppEEARS did not return a task ID."
            )

        logger.info("Submitted MODIS task: %s", task_id)

        return task_id

    def _wait_for_task(self, task_id: str) -> None:
        """Poll AppEEARS until completion or timeout."""

        deadline = time.monotonic() + (
            TASK_TIMEOUT_MINUTES * 60
        )

        while time.monotonic() < deadline:
            response = self.session.get(
                f"{APPEEARS_BASE_URL}/task/{task_id}",
                timeout=60,
            )
            response.raise_for_status()

            task_data = response.json()
            task_status = task_data.get("status")

            logger.info(
                "MODIS task %s status: %s",
                task_id,
                task_status,
            )

            if task_status == "done":
                return

            if task_status in {"error", "cancelled"}:
                raise RuntimeError(
                    f"MODIS task {task_id} failed: "
                    f"{task_data.get('message', task_status)}"
                )

            time.sleep(POLL_SECONDS)

        raise TimeoutError(
            f"MODIS task {task_id} exceeded "
            f"{TASK_TIMEOUT_MINUTES} minutes."
        )

    def _download_results(self, task_id: str) -> Path:
        """Download all files from the completed task bundle."""

        output_dir = MODIS_DATA_DIR / task_id
        output_dir.mkdir(parents=True, exist_ok=True)

        response = self.session.get(
            f"{APPEEARS_BASE_URL}/bundle/{task_id}",
            timeout=60,
        )
        response.raise_for_status()

        files = response.json().get("files", [])

        if not files:
            raise FileNotFoundError(
                f"No files found in MODIS task bundle {task_id}."
            )

        for file_info in files:
            file_id = file_info.get("file_id")
            file_name = file_info.get("file_name")

            if not file_id or not file_name:
                continue

            # Prevent remote filenames from writing outside output_dir.
            safe_file_name = Path(file_name).name
            local_path = output_dir / safe_file_name

            logger.info("Downloading MODIS file: %s", safe_file_name)

            with self.session.get(
                f"{APPEEARS_BASE_URL}/bundle/{task_id}/{file_id}",
                stream=True,
                timeout=120,
            ) as download_response:
                download_response.raise_for_status()

                with local_path.open("wb") as file:
                    for chunk in download_response.iter_content(
                        chunk_size=8192
                    ):
                        if chunk:
                            file.write(chunk)

        return output_dir

    @staticmethod
    def _find_results_csv(output_dir: Path) -> Path:
        """Find the results CSV inside the downloaded task directory."""

        csv_path = output_dir / "*results*.csv"
        csv_files = sorted(output_dir.glob("*results*.csv"))

        if not csv_files:
            logger.error(
                "No MODIS results CSV found in %s",
                output_dir,
            )
            raise FileNotFoundError(
                f"No MODIS results CSV found in {output_dir}"
            )

        csv_filename = csv_files[0]

        logger.info("Loading MODIS CSV: %s", csv_filename)

        if len(csv_files) > 1:
            logger.warning(
                "Found multiple MODIS results CSV files. "
                "Using the first: %s",
                csv_filename,
            )

        return csv_filename

    @staticmethod
    def _to_json_records(
        dataframe: pd.DataFrame,
    ) -> list[dict[str, Any]]:
        """Convert DataFrame records into JSON-compatible dictionaries."""

        records = []

        for record in dataframe.to_dict(orient="records"):
            clean_record = {}

            for key, value in record.items():
                if pd.isna(value):
                    clean_record[key] = None

                elif isinstance(value, pd.Timestamp):
                    clean_record[key] = value.date().isoformat()

                elif hasattr(value, "item"):
                    clean_record[key] = value.item()

                else:
                    clean_record[key] = value

            records.append(clean_record)

        return records

    @classmethod
    def _process_csv(cls, output_dir: Path) -> dict[str, Any]:
        """Clean MODIS data and calculate NDVI/EVI valid shares."""

        csv_filename = cls._find_results_csv(output_dir)

        df = pd.read_csv(csv_filename)

        logger.info(
            "Available MODIS CSV columns: %s",
            df.columns.tolist(),
        )

        required_columns = [
            NDVI_COLUMN,
            EVI_COLUMN,
            QA_COLUMN,
            "Date",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise KeyError(
                f"MODIS CSV is missing required columns: {missing}"
            )

        # Convert Date to datetime and sort chronologically.
        df["Date"] = pd.to_datetime(
            df["Date"],
            errors="coerce",
        )

        df = (
            df.dropna(subset=["Date"])
            .sort_values("Date")
            .reset_index(drop=True)
        )

        if df.empty:
            raise ValueError(
                "MODIS results CSV contains no valid dated observations."
            )

        # Convert vegetation indices and QA values to numeric.
        for column in [
            NDVI_COLUMN,
            EVI_COLUMN,
            QA_COLUMN,
        ]:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce",
            )

        # Preserve the notebook's cleaned columns.
        df["Clean_NDVI"] = df[NDVI_COLUMN]
        df["Clean_EVI"] = df[EVI_COLUMN]

        # Pixel reliability:
        # 0 = Good, 1 = Marginal, 2 = Snow/ice,
        # 3 = Cloudy, -1 = No data / Fill value.
        quality_counts = (
            df[QA_COLUMN]
            .value_counts(dropna=False)
            .to_dict()
        )

        logger.info(
            "MODIS pixel reliability counts: %s",
            quality_counts,
        )

        # Keep good and marginal observations.
        valid_mask = df[QA_COLUMN].isin([0, 1])

        filtered_df = df[valid_mask].copy()

        total_observations = len(df)
        valid_observations = len(filtered_df)

        logger.info(
            "MODIS observations: %s total, %s passed QA filter.",
            total_observations,
            valid_observations,
        )

        # Calculate valid shares separately for NDVI and EVI.
        ndvi_valid_share = float(
            (valid_mask & df["Clean_NDVI"].notna()).mean()
        )

        evi_valid_share = float(
            (valid_mask & df["Clean_EVI"].notna()).mean()
        )

        # Preserve the filtered DataFrame's records for downstream use.
        records = cls._to_json_records(filtered_df)

        return {
            "product": PRODUCT,
            "start_date": MODIS_START_DATE,
            "end_date": MODIS_END_DATE,
            "total_observations": total_observations,
            "valid_observations": valid_observations,
            "ndvi_valid_share": ndvi_valid_share,
            "evi_valid_share": evi_valid_share,
            "pixel_reliability_counts": {
                str(key): int(value)
                for key, value in quality_counts.items()
            },
            "data": records,
        }

    def fetch_data(
        self,
        latitude: float,
        longitude: float,
    ) -> dict[str, Any]:
        """Fetch and process MODIS data for a geographic point."""

        try:
            self._authenticate()

            task_id = self._submit_task(
                latitude=latitude,
                longitude=longitude,
            )

            self._wait_for_task(task_id)

            output_dir = self._download_results(task_id)

            result = self._process_csv(output_dir)

            result["task_id"] = task_id
            result["latitude"] = latitude
            result["longitude"] = longitude

            logger.info(
                "MODIS data processing completed for task %s.",
                task_id,
            )

            return result

        finally:
            self.session.close()
