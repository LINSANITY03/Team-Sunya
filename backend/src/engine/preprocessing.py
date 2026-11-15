"""
    Cleans and transforms data.
"""
import pandas as pd
from engine.config import RotationConfig
import re
import datetime as dt
import calendar


KC_MID = [("green manure", .90), ("pulse", 1.0), ("legume", 1.0), ("oilseed", .95), ("cereal", 1.10),
          ("tuber", 1.10), ("root", 1.05), ("vegetable", 1.05), ("fiber", 1.10), ("fibre", 1.10)]

def _norm(series: pd.Series) -> pd.Series:
    return (
        series.astype("string")
        .fillna("")
        .str.strip()
        .str.casefold()
    )

def _yes(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .isin(["yes", "y", "true", "1"])
    )

def _int_or_none(x):
    v = pd.to_numeric(x, errors="coerce")
    return None if pd.isna(v) else int(v)

def parse_gp_value(gp_val):
    """
        Parses gp_value which could be an int, float, or a string range like '100 - 120' or '110-130'.
        Returns the maximum integer found, or 0 if it cannot be parsed.
    """
    if pd.isna(gp_val):
        return 0
    if isinstance(gp_val, (int, float)):
        return int(gp_val)
    
    # Convert to string and search for numbers
    val_str = str(gp_val)
    numbers = re.findall(r"\d+(?:\.\d+)?", val_str) 
    if not numbers:
        return 0
    
    # If it's a range like "100-120", take the upper bound (or lower, depending on how strict you want to be)
    int_numbers = [int(n) for n in numbers]
    return max(int_numbers)

def prep_crops(crop_dataframe: pd.DataFrame, crop_calender_dataframe: pd.DataFrame, cfg: RotationConfig) -> pd.DataFrame:
    prepared_crops = crop_dataframe.copy().reset_index(drop=True)
    # converting terrain to boolean values
    _terrain_columns = ["terai", "hill", "mountain"]
    
    for terrain_column in _terrain_columns:
        prepared_crops[terrain_column] = _yes(prepared_crops[terrain_column])

    text_columns = ["crop", "category", "family", "function", "species"]
    for column_name in text_columns:
        prepared_crops[column_name] = (
            prepared_crops[column_name]
            .fillna("")
            .astype(str)
            .str.strip()
        )
    prepared_crops["family"] = prepared_crops["family"].str.title()

    fn = prepared_crops["function"].str.lower()
    cat = prepared_crops["category"].str.lower()
    fam = prepared_crops["family"].str.lower()

    prepared_crops["is_green_manure"] = (
        fn.str.contains("green manure", na=False)
    )
    prepared_crops["is_legume"] = (
        fam.eq("fabaceae") |
        fn.str.contains("pulse|legume", na=False)
    )
    prepared_crops["is_cash"] = (
        fn.str.contains("cash|fiber|fibre|oilseed", na=False)
    )
    prepared_crops["is_food"] = (
        fn.str.contains("food|staple|pulse", na=False)
    )
    prepared_crops["heavy_feeder"] = (
        cat.str.contains("cereal|tuber", na=False) &
        ~prepared_crops["is_legume"]
    )

    # Estimate mean crop coefficient if it is not provided
    if "kc_mean" not in prepared_crops.columns:
        def estimate_crop_coefficient(crop_row):
            crop_description = (crop_row["category"] + " " + crop_row["function"])
            matching_coefficient = next(
                (
                    coefficient
                    for keyword, coefficient in KC_MID
                    if keyword in crop_description
                ),
                1.0
            )

            return 0.85 * matching_coefficient

        prepared_crops["kc_mean"] = prepared_crops.apply(
            estimate_crop_coefficient,
            axis=1
        )
    
    # Create income index if it is not provided
    if "income_index" not in prepared_crops.columns:
        prepared_crops["income_index"] = (
            prepared_crops["is_cash"].astype(float)
        )
    
    # Normalize income index
    prepared_crops["income_index"] = pd.to_numeric(prepared_crops["income_index"],errors="coerce",).fillna(0.0)
    max_income = prepared_crops["income_index"].max()
    if max_income > 0:
        prepared_crops["income_index"] /= max_income
    else:
        prepared_crops["income_index"] = 0.0

    prepared_crops["data_flag"] = ""

    needed = {"crop", "aez", "harv_early_month", "harv_early_day", "sow_early_month", "sow_early_day", "gp_value"}

    if needed.issubset(crop_calender_dataframe.columns):
        cal = crop_calender_dataframe
        cal_crop, cal_aez = _norm(cal["crop"]), _norm(cal["aez"])
        for i, crop_row in prepared_crops.iterrows():
            flags = []
            for terrain in _terrain_columns:
                if not crop_row[terrain]:
                    continue
                rows = cal[(cal_crop == crop_row["crop"].lower()) & (cal_aez == terrain)]
                for _, cr in rows.iterrows():
                    if "all_year" in cal.columns and _norm(pd.Series([cr["all_year"]])).iloc[0] in ("yes", "true", "1", "y"):
                        continue
                    gp = parse_gp_value(cr["gp_value"])
                    parts = [_int_or_none(cr[c]) for c in ("sow_early_month", "sow_early_day",
                                                           "harv_early_month", "harv_early_day")]
                    if gp <= 0 or gp >= 360 or any(p is None for p in parts):
                        continue
                    try:
                        expected = (mk_date(2001, parts[2], parts[3]) - mk_date(2001, parts[0], parts[1])).days % 365
                    except ValueError:
                        continue
                    if abs(expected - min(gp, 364)) > cfg.harvest_mismatch_tol_days:
                        flags.append(f"{terrain}: early harvest implies {expected} d but growing period is {gp} d")
            prepared_crops.loc[i, "data_flag"] = "; ".join(flags)
    return prepared_crops

def mk_date(y, m, d):
    """
        Helper function to return datetime format.
    """
    month = int(m)
    day = int(d)
    last_day = calendar.monthrange(year=y, month=month)[1]

    return dt.date(
        y,
        month,
        min(day, last_day)
    )

class Preprocessor:

    def __init__(
        self,
        datasets: dict,
        config: RotationConfig,
    ) -> None:
        self.datasets = datasets
        self.config = config

    def preprocess(self) -> dict:
        crop_data = prep_crops(
            crop_dataframe=self.datasets["crop_data"],
            crop_calender_dataframe=self.datasets["crop_calendar"],
            cfg=self.config,
        )

        return {
            "crop_data": crop_data,
            "crop_calendar": self.datasets["crop_calendar"].copy(),
            "weather_data": self.datasets["weather_data"].copy(),
            "soil_data": self.datasets["soil_data"].copy(),
            "elevation_data": self.datasets["elevation_data"].copy(),
            "modis_data": self.datasets["modis_data"].copy(),
        }
