
from functools import lru_cache

import numpy as np
import pandas as pd
import rasterio
from rasterio.warp import transform


class SoilService:
    """
        Extract soil properties from ISRIC SoilGrids rasters. For the current purpose,
        we are using depth 30-60cm as a average.
    """

    SOIL_PROPERTIES = {
        "phh2o": {"depth": "30-60cm", "scale": 10, "unit": "pH"},
        "soc": {"depth": "30-60cm", "scale": 10, "unit": "g/kg"},
        "clay": {"depth": "30-60cm", "scale": 10, "unit": "%"},
        "sand": {"depth": "30-60cm", "scale": 10, "unit": "%"},
        "silt": {"depth": "30-60cm", "scale": 10, "unit": "%"},
        "bdod": {"depth": "30-60cm", "scale": 100, "unit": "kg/dm3"},
        "nitrogen": {"depth": "30-60cm", "scale": 100, "unit": "g/kg"},
    }

    WATER_PROPERTIES = {
        "wv0010": {
            "depth": "30-60cm",
            "scale": 10,
            "unit": "volumetric_percent",
        },
        "wv0033": {
            "depth": "30-60cm",
            "scale": 10,
            "unit": "volumetric_percent",
        },
        "wv1500": {
            "depth": "30-60cm",
            "scale": 10,
            "unit": "volumetric_percent",
        },
    }

    ALL_PROPERTIES = {
        **SOIL_PROPERTIES,
        **WATER_PROPERTIES,
    }

    PROPERTY_RENAME = {
        "phh2o": "ph",
        "soc": "soc",
        "clay": "clay",
        "sand": "sand",
        "silt": "silt",
        "bdod": "bdod",
        "nitrogen": "nitrogen",
        "wv0010": "wv10",
        "wv0033": "wv33",
        "wv1500": "wv1500",
    }

    @classmethod
    def _get_raster_url(cls, prop: str, meta: dict) -> str:
        if prop in cls.WATER_PROPERTIES:
            return (
                "https://files.isric.org/soilgrids/latest/"
                f"data_aggregated/1000m/{prop}/"
                f"{prop}_{meta['depth']}_mean_1000.tif"
            )

        return (
            "https://files.isric.org/soilgrids/latest/data/"
            f"{prop}/{prop}_{meta['depth']}_mean.vrt"
        )

    @classmethod
    @lru_cache(maxsize=512)
    def _extract_soil_value(
        cls,
        prop: str,
        latitude: float,
        longitude: float,
    ) -> float | None:

        meta = cls.ALL_PROPERTIES[prop]
        url = cls._get_raster_url(prop, meta)

        try:
            with rasterio.open(url) as src:
                if src.crs is None:
                    raise ValueError(f"{prop}: Raster has no CRS.")

                xs, ys = transform(
                    "EPSG:4326",
                    src.crs,
                    [longitude],
                    [latitude],
                )

                raw_value = next(
                    src.sample([(xs[0], ys[0])], masked=True)
                )[0]

                if np.ma.is_masked(raw_value):
                    return None

                raw_value = float(raw_value)

                if not np.isfinite(raw_value):
                    return None

                if src.nodata is not None and raw_value == src.nodata:
                    return None

                if raw_value <= -9999:
                    return None

                return raw_value / meta["scale"]

        except Exception as exc:
            raise RuntimeError(
                f"Failed to extract soil property '{prop}'."
            ) from exc

    @classmethod
    def get_soil_properties(
        cls,
        latitude: float,
        longitude: float,
    ) -> pd.DataFrame:

        extracted_records = []

        for prop, meta in cls.ALL_PROPERTIES.items():
            try:
                value = cls._extract_soil_value(
                    prop,
                    latitude,
                    longitude,
                )
            except RuntimeError:
                value = None

            extracted_records.append({
                "Property": cls.PROPERTY_RENAME[prop],
                "Depth": meta["depth"],
                "Value": value,
                "Unit": meta["unit"],
            })

        df_soil = pd.DataFrame(extracted_records)

        df_soil = cls._calculate_available_water_capacity(df_soil)

        return df_soil

    @staticmethod
    def _calculate_available_water_capacity(
        df_soil: pd.DataFrame,
    ) -> pd.DataFrame:

        water = df_soil.set_index("Property")["Value"]

        theta_33 = water.get("wv33")
        theta_1500 = water.get("wv1500")

        if pd.notna(theta_33) and pd.notna(theta_1500):
            awc_fraction = (theta_33 - theta_1500) / 100

            if awc_fraction >= 0:
                # The extracted values represent the 30-60 cm layer.
                layer_depth_mm = 300

                derived_records = [
                    {
                        "Property": "awc_fraction",
                        "Depth": "30-60cm",
                        "Value": awc_fraction,
                        "Unit": "m3/m3",
                    },
                    {
                        "Property": "awc_mm_in_layer",
                        "Depth": "30-60cm",
                        "Value": awc_fraction * layer_depth_mm,
                        "Unit": "mm",
                    },
                ]

                df_soil = pd.concat(
                    [df_soil, pd.DataFrame(derived_records)],
                    ignore_index=True,
                )

        return df_soil
