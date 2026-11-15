from functools import lru_cache

import pandas as pd
import requests


class NASAPowerService:
    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    START_DATE = "20160101"
    END_DATE = "20250101"

    PARAMETERS = (
        "PRECTOTCORR,T2M,T2M_MAX,T2M_MIN," "RH2M,WS2M,ALLSKY_SFC_SW_DWN,GWETPROF"
    )

    COLUMN_RENAME = {
        "PRECTOTCORR": "precip",
        "T2M": "tmean",
        "T2M_MAX": "tmax",
        "T2M_MIN": "tmin",
        "RH2M": "rh",
        "WS2M": "wind",
        "ALLSKY_SFC_SW_DWN": "rs",
        "GWETPROF": "wet",
    }

    @classmethod
    @lru_cache(maxsize=32)
    def fetch_daily_data(
        self,
        latitude: float,
        longitude: float,
    ) -> pd.DataFrame:
        """
        Fetch daily NASA POWER agricultural climate data
        for the supplied coordinates.
        """

        params = {
            "parameters": self.PARAMETERS,
            "community": "AG",
            "longitude": longitude,
            "latitude": latitude,
            "start": self.START_DATE,
            "end": self.END_DATE,
            "format": "JSON",
            "time-standard": "UTC",
        }

        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()

        except requests.RequestException as exc:
            raise RuntimeError("Failed to retrieve data from NASA POWER.") from exc

        except ValueError as exc:
            raise RuntimeError("NASA POWER returned an invalid JSON response.") from exc

        try:
            parameter_data = payload["properties"]["parameter"]

            df = pd.DataFrame(parameter_data)

            df.index.name = "date"
            df = df.reset_index()

            df["date"] = pd.to_datetime(
                df["date"],
                format="%Y%m%d",
                errors="raise",
            )

            df = df.rename(columns=self.COLUMN_RENAME)

            df = df.sort_values("date").reset_index(drop=True)

        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(
                "NASA POWER response did not contain the expected data."
            ) from exc

        return df
