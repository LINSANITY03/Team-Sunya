
from functools import lru_cache
import math

import requests


class TerrainService:
    BASE_URL = "https://api.open-meteo.com/v1/elevation"

    LAND_TERRAIN = {
        0: "Terai",
        1: "Hill",
        2: "Mountain",
    }

    @staticmethod
    def _classify_terrain(elevation: float) -> str:
        if elevation < 1000:
            return TerrainService.LAND_TERRAIN[0]
        elif elevation < 2000:
            return TerrainService.LAND_TERRAIN[1]
        return TerrainService.LAND_TERRAIN[2]

    @staticmethod
    @lru_cache(maxsize=128)
    def _fetch_elevation(
        latitude: float,
        longitude: float,
    ) -> float:

        params = {
            "latitude": latitude,
            "longitude": longitude,
        }

        try:
            response = requests.get(
                TerrainService.BASE_URL,
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

        except requests.RequestException as exc:
            raise RuntimeError(
                "Failed to retrieve elevation from Open-Meteo."
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                "Open-Meteo returned an invalid JSON response."
            ) from exc

        try:
            elevation_data = data["elevation"]

            if not isinstance(elevation_data, list) or not elevation_data:
                raise ValueError("Elevation data is missing.")

            elevation = float(elevation_data[0])

            if not math.isfinite(elevation):
                raise ValueError("Elevation is not a valid finite number.")

            return elevation

        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError(
                "Could not parse elevation from Open-Meteo response."
            ) from exc

    @classmethod
    def get_terrain_elevation(
        cls,
        latitude: float,
        longitude: float,
    ) -> dict:

        try:
            elevation = cls._fetch_elevation(latitude, longitude)
        except RuntimeError:
            return {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_m": None,
                "terrain": None,
            }

        return {
            "latitude": latitude,
            "longitude": longitude,
            "elevation_m": elevation,
            "terrain": cls._classify_terrain(elevation),
        }
