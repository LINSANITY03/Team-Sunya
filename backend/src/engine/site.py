
from datetime import date
import numpy as np
import pandas as pd

from engine.config import RotationConfig


# -------------------------------------------------------------------
# Constants
# -------------------------------------------------------------------

CAL = pd.date_range(
    "2000-01-01",
    "2070-12-31",
    freq="D",
)

ORD0 = date(2000, 1, 1).toordinal()

DEFAULT_AWC_FRAC = 0.12


# -------------------------------------------------------------------
# Date utilities
# -------------------------------------------------------------------

def doy_365(dates: pd.Series) -> pd.Series:
    """
    Convert dates to a consistent 1..365 day-of-year.

    February 29 is grouped with February 28.
    """

    dates = pd.to_datetime(dates)

    doy = dates.dt.dayofyear.copy()

    after_feb = dates.dt.is_leap_year & (dates.dt.month > 2)
    doy = doy - after_feb.astype(int)

    feb29 = (dates.dt.month == 2) & (dates.dt.day == 29)
    doy.loc[feb29] = 59

    return doy


DOY_IDX = doy_365(pd.Series(CAL)).to_numpy() - 1


def _circ_smooth(
    values: np.ndarray,
    window: int = 15,
) -> np.ndarray:
    """Apply circular moving-average smoothing to 365 values."""

    values = np.asarray(values, dtype=float)

    if len(values) != 365:
        raise ValueError(
            "Circular smoothing expects exactly 365 values."
        )

    if window < 1 or window % 2 == 0:
        raise ValueError(
            "Smoothing window must be a positive odd number."
        )

    padding = window // 2

    extended = np.r_[
        values[-padding:],
        values,
        values[:padding],
    ]

    return np.convolve(
        extended,
        np.ones(window) / window,
        mode="valid",
    )


# -------------------------------------------------------------------
# Site
# -------------------------------------------------------------------

class Site:
    """
    Soil profile, weather climatology, MODIS climatology,
    and cumulative arrays for efficient seasonal calculations.
    """

    def __init__(
        self,
        power_df: pd.DataFrame,
        soilgrid_df: pd.DataFrame,
        modis_df: pd.DataFrame,
        cfg: RotationConfig,
        ndvi_valid_share: float | None = None,
        evi_valid_share: float | None = None,
    ) -> None:

        self._power_df = power_df.copy()
        self._soil_df = soilgrid_df.copy()
        self._modis_df = modis_df.copy()

        self.ndvi_valid_share = ndvi_valid_share
        self.evi_valid_share = evi_valid_share

        self._validate_inputs()

        # -----------------------------------------------------------
        # Soil preparation
        # -----------------------------------------------------------

        self._soil = self._prepare_soil(self._soil_df)

        wv33 = self._soil.get("wv33", np.nan)
        wv15 = self._soil.get("wv1500", np.nan)

        if pd.notna(wv33) and pd.notna(wv15):

            divisor = (
                1000 if wv33 > 100
                else 100 if wv33 > 1
                else 1
            )

            self.awc_frac = max(
                (wv33 - wv15) / divisor,
                0.0,
            )

        else:
            self.awc_frac = DEFAULT_AWC_FRAC

        # -----------------------------------------------------------
        # NASA POWER weather preparation
        # -----------------------------------------------------------

        self._power_df["date"] = pd.to_datetime(
            self._power_df["date"],
            errors="coerce",
        )

        self._power_df = (
            self._power_df
            .dropna(subset=["date"])
            .sort_values("date")
            .reset_index(drop=True)
        )

        self.n_weather_days = len(self._power_df)

        self._power_df["doy"] = doy_365(
            self._power_df["date"]
        ).values

        if (
            "tmean" not in self._power_df.columns
            or self._power_df["tmean"].isna().all()
        ):
            self._power_df["tmean"] = (
                self._power_df["tmax"]
                + self._power_df["tmin"]
            ) / 2

        weather_vars = [
            variable
            for variable in [
                "tmean",
                "tmax",
                "tmin",
                "rh",
                "wind",
                "rs",
                "wet",
                "precip",
            ]
            if variable in self._power_df.columns
        ]

        if not {"tmean", "rs"}.issubset(weather_vars):
            raise ValueError(
                "NASA POWER data must contain tmean and rs."
            )

        weather_clim = (
            self._power_df
            .groupby("doy")[weather_vars]
            .mean()
            .reindex(range(1, 366))
            .interpolate(limit_direction="both")
        )

        if weather_clim.isna().any().any():
            raise ValueError(
                "Weather climatology still contains missing values."
            )

        for variable in weather_clim.columns:
            weather_clim[variable] = _circ_smooth(
                weather_clim[variable].values
            )

        # -----------------------------------------------------------
        # Reference evapotranspiration
        # -----------------------------------------------------------

        rs_mj = (
            weather_clim["rs"] * 3.6
            if cfg.rs_unit == "kWh"
            else weather_clim["rs"]
        )

        weather_clim["et0"] = np.clip(
            0.0135
            * (weather_clim["tmean"] + 17.8)
            * rs_mj
            / 2.45,
            0,
            None,
        )

        self.weather_clim = weather_clim

        self.has_precip = "precip" in weather_clim.columns

        # -----------------------------------------------------------
        # Map climatology to the complete calendar
        # -----------------------------------------------------------

        self.daily = {
            variable: weather_clim[variable].to_numpy()[DOY_IDX]
            for variable in weather_clim.columns
        }

        # -----------------------------------------------------------
        # Cumulative sums
        # -----------------------------------------------------------

        self.cum = {
            variable: np.r_[
                0.0,
                np.cumsum(values),
            ]
            for variable, values in self.daily.items()
        }

        # -----------------------------------------------------------
        # MODIS preparation
        # -----------------------------------------------------------

        self.prepare_modis_daily()

    # ----------------------------------------------------------------
    # Input validation
    # ----------------------------------------------------------------

    def _validate_inputs(self) -> None:
        """Validate required input datasets."""

        if self._power_df.empty:
            raise ValueError("NASA POWER dataset is empty.")

        if self._soil_df.empty:
            raise ValueError("SoilGrids dataset is empty.")

        if self._modis_df.empty:
            raise ValueError("MODIS dataset is empty.")

        required_weather = {"date", "tmax", "tmin", "rs"}

        missing_weather = (
            required_weather - set(self._power_df.columns)
        )

        if missing_weather:
            raise ValueError(
                "NASA POWER dataset is missing columns: "
                f"{sorted(missing_weather)}"
            )

        required_modis = {
            "Date",
            "Clean_NDVI",
            "Clean_EVI",
        }

        missing_modis = (
            required_modis - set(self._modis_df.columns)
        )

        if missing_modis:
            raise ValueError(
                "MODIS dataset is missing columns: "
                f"{sorted(missing_modis)}"
            )

    # ----------------------------------------------------------------
    # Soil preparation
    # ----------------------------------------------------------------

    @staticmethod
    def _prepare_soil(df: pd.DataFrame) -> pd.Series:
        """Prepare SoilGrids data in either long or wide format."""

        data = df.copy()

        aliases = {
            "phh2o": "ph",
            "wv0010": "wv10",
            "wv0033": "wv33",
            "bdod": "bdod",
        }

        # Long format
        if {"Property", "Depth", "Value"}.issubset(data.columns):

            data["Property"] = (
                data["Property"]
                .astype(str)
                .str.lower()
            )

            # Preserve the notebook's original 30-60cm selection.
            surface = data[
                data["Depth"].astype(str) == "30-60cm"
            ].copy()

            if surface.empty:
                raise ValueError(
                    "No 30-60cm SoilGrids layer found. "
                    "Choose and aggregate soil depths explicitly."
                )

            surface["Value"] = pd.to_numeric(
                surface["Value"],
                errors="coerce",
            )

            soil = (
                surface
                .groupby("Property")["Value"]
                .median()
            )

            soil = soil.rename(index=aliases)

        # Wide format
        else:

            rename = {
                key: value
                for key, value in aliases.items()
                if key in data.columns
            }

            data = data.rename(columns=rename)

            soil = data.select_dtypes(
                include=np.number
            ).median()

        # Convert SoilGrids pH*10 if necessary.
        if "ph" in soil.index and pd.notna(soil["ph"]):

            if soil["ph"] > 14:
                soil["ph"] = soil["ph"] / 10

        return soil

    # ----------------------------------------------------------------
    # MODIS preparation
    # ----------------------------------------------------------------

    def prepare_modis_daily(self) -> None:
        """
        Prepare MODIS NDVI/EVI seasonal climatologies.

        Maps historical seasonal patterns to the complete
        calendar, including dates after the last observation.
        """

        modis_dataframe = self._modis_df.copy()

        modis_dataframe = modis_dataframe.rename(
            columns={
                "Date": "date",
                "Clean_NDVI": "ndvi",
                "Clean_EVI": "evi",
            }
        )

        modis_dataframe["date"] = pd.to_datetime(
            modis_dataframe["date"],
            errors="coerce",
        )

        for variable in ["ndvi", "evi"]:
            modis_dataframe[variable] = pd.to_numeric(
                modis_dataframe[variable],
                errors="coerce",
            )

        modis_dataframe = modis_dataframe.dropna(
            subset=["date"]
        ).copy()

        if modis_dataframe.empty:
            raise ValueError(
                "MODIS dataset has no valid observation dates."
            )

        modis_dataframe["doy"] = doy_365(
            modis_dataframe["date"]
        ).to_numpy()

        self.modis_dataframe = modis_dataframe
        self.modis_climatology = {}

        for variable in ["ndvi", "evi"]:

            observations = (
                modis_dataframe
                .dropna(subset=[variable])
                .groupby("doy")[variable]
                .mean()
            )

            seasonal_climatology = observations.reindex(
                range(1, 366)
            )

            valid_days = seasonal_climatology.notna().to_numpy()

            if valid_days.sum() < 2:
                raise ValueError(
                    f"Not enough historical {variable.upper()} "
                    "observations to build seasonal climatology."
                )

            known_positions = np.where(valid_days)[0]
            known_values = seasonal_climatology.to_numpy()[valid_days]

            extended_positions = np.concatenate([
                known_positions - 365,
                known_positions,
                known_positions + 365,
            ])

            extended_values = np.concatenate([
                known_values,
                known_values,
                known_values,
            ])

            all_positions = np.arange(365)

            interpolated_values = np.interp(
                all_positions,
                extended_positions,
                extended_values,
            )

            smoothed_values = _circ_smooth(
                interpolated_values,
                window=15,
            )

            seasonal_climatology = pd.Series(
                smoothed_values,
                index=range(1, 366),
            )

            self.modis_climatology[variable] = (
                seasonal_climatology
            )

            future_daily_values = (
                seasonal_climatology.to_numpy()[DOY_IDX]
            )

            self.daily[variable] = future_daily_values

            self.cum[variable] = np.r_[
                0.0,
                np.cumsum(future_daily_values),
            ]

            # These are climatology availability counts,
            # NOT actual satellite observation counts.
            self.cum[f"{variable}_count"] = np.r_[
                0,
                np.cumsum(
                    np.isfinite(future_daily_values).astype(int)
                ),
            ]

        self.ndvi_max = float(
            np.max(self.daily["ndvi"])
        )

    # ----------------------------------------------------------------
    # Seasonal calculations
    # ----------------------------------------------------------------

    @staticmethod
    def _get_date_index(value: date) -> int:
        """Convert a date into its calendar array index."""

        index = value.toordinal() - ORD0

        if index < 0 or index >= len(CAL):
            raise ValueError(
                f"Date {value} is outside the supported "
                "calendar range 2000-01-01 to 2070-12-31."
            )

        return index

    def span_sum(
        self,
        variable_name: str,
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate total daily values over [start_date, end_date).

        Start date is inclusive; end date is exclusive.
        """

        if variable_name not in self.cum:
            raise KeyError(
                f"Unknown variable: {variable_name}"
            )

        if end_date <= start_date:
            raise ValueError(
                "End date must be after start date."
            )

        start_index = self._get_date_index(start_date)
        end_index = self._get_date_index(end_date)

        if end_index > len(CAL):
            raise ValueError(
                "End date is outside the supported calendar."
            )

        total = (
            self.cum[variable_name][end_index]
            - self.cum[variable_name][start_index]
        )

        return float(total)

    def span_mean(
        self,
        variable_name: str,
        start_date: date,
        end_date: date,
    ) -> float:
        """
        Calculate average daily values over [start_date, end_date).

        For NDVI/EVI, use the climatology availability count.
        """

        if variable_name not in self.cum:
            raise KeyError(
                f"Unknown variable: {variable_name}"
            )

        if end_date <= start_date:
            raise ValueError(
                "End date must be after start date."
            )

        start_index = self._get_date_index(start_date)
        end_index = self._get_date_index(end_date)

        if end_index > len(CAL):
            raise ValueError(
                "End date is outside the supported calendar."
            )

        total = (
            self.cum[variable_name][end_index]
            - self.cum[variable_name][start_index]
        )

        if variable_name in ["ndvi", "evi"]:

            valid_count = (
                self.cum[f"{variable_name}_count"][end_index]
                - self.cum[f"{variable_name}_count"][start_index]
            )

            if valid_count == 0:
                return np.nan

            return float(total / valid_count)

        number_of_days = (end_date - start_date).days

        return float(total / number_of_days)
