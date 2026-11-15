from typing import Any
import pandas as pd
import numpy as np
import datetime as dt
import itertools
import calendar

from engine.preprocessing import parse_gp_value
from engine.site import Site
from engine.config import RotationConfig
from engine.farmer_priorities import FarmerPriority
from engine.field_profile import FieldProfile


def mk_date(y, m, d):
    """
    Helper function to return a valid datetime date.

    Adjusts the day if it exceeds the number of days
    in the specified month.
    """
    month = int(m)
    day = int(d)

    last_day = calendar.monthrange(
        year=y,
        month=month,
    )[1]

    return dt.date(
        y,
        month,
        min(day, last_day),
    )


def candidate_sowing_dates(
    field_ready_date: dt.date,
    crop,
    crop_calender_df,
    terrain_str,
    max_fallow_days=120,
    step_days=7,
):
    """
    Returns multiple valid sowing dates for a crop.

    Searches all calendar windows within the allowed
    fallow period, rather than selecting only the earliest.
    """

    crop_name = str(
        crop.crop if hasattr(crop, "crop") else crop
    ).strip().lower()

    terrain = str(terrain_str).strip().lower()

    filtered = crop_calender_df[
        (
            crop_calender_df["crop"]
            .astype(str).str.strip().str.lower() == crop_name
        )
        & (
            crop_calender_df["aez"]
            .astype(str).str.strip().str.lower() == terrain
        )
    ]

    if filtered.empty:
        print(f"[NO CALENDAR MATCH] {crop_name}, {terrain}")
        return []

    latest_allowed = field_ready_date + dt.timedelta(
        days=max_fallow_days
    )

    candidates = set()

    for idx, row in filtered.iterrows():

        try:
            # Year-round crops.
            all_year = str(row["all_year"]).strip().lower()

            if all_year in ("yes", "true", "1", "y"):
                current = field_ready_date

                while current <= latest_allowed:
                    candidates.add((current, idx))
                    current += dt.timedelta(days=step_days)

                continue

            early_month = int(row["sow_early_month"])
            early_day = int(row["sow_early_day"])
            late_month = int(row["sow_late_month"])
            late_day = int(row["sow_late_day"])

            # Check all relevant calendar years.
            for year in range(
                field_ready_date.year - 1,
                latest_allowed.year + 2,
            ):

                window_start = mk_date(
                    year, early_month, early_day
                )

                window_end = mk_date(
                    year, late_month, late_day
                )

                # Handle windows crossing into the next year.
                if window_end < window_start:
                    window_end = mk_date(
                        year + 1, late_month, late_day
                    )

                # Intersect calendar window with allowed dates.
                actual_start = max(
                    window_start,
                    field_ready_date,
                )

                actual_end = min(
                    window_end,
                    latest_allowed,
                )

                if actual_start > actual_end:
                    continue

                current = actual_start

                while current <= actual_end:
                    candidates.add((current, idx))
                    current += dt.timedelta(days=step_days)

                # Include the final valid date.
                candidates.add((actual_end, idx))

        except (ValueError, TypeError, KeyError) as e:
            print(
                f"[INVALID CALENDAR ROW] index={idx}, "
                f"crop={crop_name}, error={e}"
            )

    result = sorted(
        candidates,
        key=lambda x: (x[0], x[1]),
    )

    return result


def priority_weight(p):
    """
    Normalize farmer priorities into weights for rotation scoring.

    Priorities:
    - profit
    - food_security
    - soil_health
    - water_saving
    - low_risk
    """

    default_t_weight = (
        p.profit
        + p.food_security
        + p.soil_health
        + p.water_saving
        + p.low_risk
    )

    if default_t_weight == 0:
        raise ValueError(
            "User need to select a priority"
        )

    total_weight = max(default_t_weight, 1e-9)

    n = lambda x: x / total_weight

    return {
        "soil_fit": n(p.soil_health) * 0.5,
        "water_fit": n(p.water_saving),
        "timing": n(p.low_risk),
        "rotation_health": n(p.soil_health) * 0.5,
        "ndvi_support": 0.0,
        "profit": n(p.profit),
        "food": n(p.food_security),
    }


def terrain_check(field: FieldProfile, crop):
    """
    Check whether a crop is suitable for the field's terrain.

    Returns:
        bool: True if the crop is suitable, otherwise False.
    """

    if not field or not getattr(field, "terrain", None):
        print("Error: Field object or terrain attribute is missing.")
        return False

    terrain_col = str(field.terrain).strip().lower()

    if terrain_col not in crop.index:
        print(f"Terrain column '{terrain_col}' not found in crop data.")
        return False

    suitability = crop[terrain_col]
    truthy_values = {"yes", "true", "y", "1", True, 1}

    if isinstance(suitability, str):
        suitability_check = suitability.strip().lower()
    else:
        suitability_check = suitability

    if suitability_check in truthy_values:
        return True

    return False


def soil_check(crop, site: Site, field: FieldProfile, cfg: RotationConfig):
    """
    Evaluates whether a particular crop is suitable for the field's soil
    conditions.

    Checks:
    1. Soil pH (acidity/alkalinity).
    2. Soil depth (whether roots have enough space).
    3. Soil texture (clay and sand percentages).
    4. Soil compaction (bulk density).

    Then calculates a soil suitability score between 0 and 1.
    """

    s, reasons = site._soil, []

    # Check soil pH against the crop's absolute range.
    ph = float(s.ph)

    if ph < crop.ph_abs_min or ph > crop.ph_abs_max:
        reasons.append(
            f"soil pH {ph:.1f} outside {crop.crop}'s absolute range "
            f"{crop.ph_abs_min}-{crop.ph_abs_max}"
        )

    if crop.ph_opt_min <= ph <= crop.ph_opt_max:
        ph_score = 1.0
    elif ph < crop.ph_opt_min:
        ph_score = (
            (ph - crop.ph_abs_min)
            / max(crop.ph_opt_min - crop.ph_abs_min, 1e-6)
        )
    else:
        ph_score = (
            (crop.ph_abs_max - ph)
            / max(crop.ph_abs_max - crop.ph_opt_max, 1e-6)
        )

    ph_score = float(np.clip(ph_score, 0, 1))

    # Check whether the soil is deep enough for the crop's roots.
    if field.soil_depth_cm < (
        cfg.min_soil_depth_ratio * crop.rooting_depth_m * 100
    ):
        reasons.append(
            f"soil depth {field.soil_depth_cm:.0f} cm too shallow for "
            f"rooting depth {crop.rooting_depth_m * 100:.0f} cm"
        )

    depth_score = float(
        np.clip(
            field.soil_depth_cm / (crop.rooting_depth_m * 100),
            0,
            1,
        )
    )

    # Read soil texture percentages.
    clay, sand, silt = float(s.clay), float(s.sand), float(s.silt)

    # Check whether soil fractions are valid.
    if not all(0 <= x <= 100 for x in [clay, sand, silt]):
        raise ValueError(
            "Soil texture percentages must be between 0 and 100."
        )

    # Soil fractions should approximately sum to 100%.
    texture_total = clay + sand + silt

    if not 95 <= texture_total <= 105:
        raise ValueError(
            f"Invalid soil texture composition: "
            f"clay + sand + silt = {texture_total:.1f}%"
        )

    # Check whether the crop belongs to a tuber or root category.
    root_crop = any(
        k in crop.category.lower()
        for k in ["tuber", "root"]
    )

    if root_crop and clay > cfg.clay_max_root_crops:
        reasons.append(
            f"clay {clay:.0f}% too heavy for tuber/root crop"
        )

    # Calculate texture penalty score.
    tex_penalty = 0.0

    if clay > 50:
        tex_penalty += 0.4

    if sand > 70:
        tex_penalty += 0.3

    if silt > 80:
        tex_penalty += 0.2

    tex_score = float(np.clip(1.0 - tex_penalty, 0, 1))

    # Check soil compaction.
    bd = float(s.bdod)

    if bd >= cfg.bd_reject:
        reasons.append(
            f"bulk density {bd:.2f} kg/dm3 restricts root growth"
        )

    # Calculate bulk density score.
    bd_score = 0.7 if bd > 1.55 else 1.0

    # Calculate final soil fit.
    fit = float(np.mean([
        ph_score,
        depth_score,
        tex_score,
        bd_score,
    ]))

    return (
        not reasons,
        "; ".join(reasons),
        {
            "soil_fit": fit,
            "ph_score": ph_score,
        },
    )


def generate_candidates(
    number_of_crops: int,
    rotation_length: int,
    max_candidates: int,
    seed: int,
):
    """
    Generates possible crop rotations.

    Args:
        number_of_crops (int): Number of available crops.
        rotation_length (int): Number of crops in each rotation.
        max_candidates (int): Maximum number of candidates to generate.
        seed (int): Random seed.
    """

    if (
        number_of_crops <= 0
        or rotation_length <= 0
        or max_candidates <= 0
    ):
        raise ValueError(
            "number_of_crops, rotation_length, and max_candidates "
            "must be positive."
        )

    total = number_of_crops ** rotation_length

    # Generate every possible sequence if the total is within the limit.
    if total <= max_candidates:
        return list(
            itertools.product(
                range(number_of_crops),
                repeat=rotation_length,
            )
        )

    random_generator = np.random.default_rng(seed)

    unique_candidates = set()

    while len(unique_candidates) < max_candidates:
        remaining_candidates = max_candidates - len(unique_candidates)
        batch_size = min(remaining_candidates * 2, 10000)

        samples = random_generator.integers(
            0,
            number_of_crops,
            size=(batch_size, rotation_length),
        )

        unique_candidates.update(map(tuple, samples))

    return sorted(unique_candidates)[:max_candidates]


def rotation_check(
    rotation_crops,
    cfg: RotationConfig,
    soil: pd.Series,
):
    """
    Checks the health of a crop rotation.

    Args:
        rotation_crops: Crops in the proposed rotation.
        cfg: Rotation settings.
        soil: Soil-property series.

    Returns:
        tuple: Rejection reasons and rotation health score.
    """

    rotation_length = len(rotation_crops)

    if rotation_length == 0:
        raise ValueError("Rotation must contain at least one crop.")

    rejection_reasons = []

    # Compare every pair of crops.
    for first_index in range(rotation_length):
        for second_index in range(first_index + 1, rotation_length):
            first_crop = rotation_crops[first_index]
            second_crop = rotation_crops[second_index]

            cycle_distance = second_index - first_index

            # Account for cyclic rotations.
            if cfg.cyclic:
                cycle_distance = min(
                    cycle_distance,
                    rotation_length - cycle_distance,
                )

            # Check whether the same species are too close together.
            if (
                first_crop.species == second_crop.species
                and cycle_distance < 2
            ):
                rejection_reasons.append(
                    f"same species ({first_crop.species}) repeated "
                    f"{cycle_distance} cycle(s) apart"
                )

            # Check whether crops from the same family are too close.
            elif first_crop.family == second_crop.family:
                required_family_gap = cfg.family_gap_overrides.get(
                    first_crop.family,
                    cfg.default_family_gap,
                )

                if cycle_distance < required_family_gap:
                    rejection_reasons.append(
                        f"family {first_crop.family} "
                        f"({first_crop.crop} & {second_crop.crop}) "
                        f"only {cycle_distance} cycle(s) apart; "
                        f"needs >= {required_family_gap}"
                    )

    # Check whether the rotation contains a legume.
    contains_legume = any(
        crop.is_legume for crop in rotation_crops
    )

    if cfg.require_legume and not contains_legume:
        rejection_reasons.append(
            "No legume or green manure in the rotation."
        )

    # Calculate family diversity score.
    unique_families = {
        crop.family for crop in rotation_crops
    }

    family_diversity_score = (
        len(unique_families) / rotation_length
    )

    # Calculate nitrogen-related rotation score.
    soil_nitrogen = soil.get("nitrogen", np.nan)

    if pd.isna(soil_nitrogen):
        raise ValueError(
            "Soil nitrogen is missing; cannot calculate "
            "the nitrogen-related rotation score."
        )

    nitrogen_need_score = float(
        np.clip(
            1 - float(soil_nitrogen) / cfg.n_ok_g_per_kg,
            0,
            1,
        )
    )

    # Calculate legume score.
    legume_score = (
        0.6 + 0.4 * nitrogen_need_score
        if contains_legume
        else 0.0
    )

    # Calculate root-depth alternation score.
    rooting_depths_cm = [
        crop.rooting_depth_m * 100
        for crop in rotation_crops
    ]

    if rotation_length > 1 and max(rooting_depths_cm) > 0:
        consecutive_root_depth_differences = [
            abs(
                rooting_depths_cm[index]
                - rooting_depths_cm[index - 1]
            )
            for index in range(1, rotation_length)
        ]

        average_root_depth_difference = np.mean(
            consecutive_root_depth_differences
        )

        root_depth_alternation_score = (
            average_root_depth_difference
            / max(rooting_depths_cm)
        )
    else:
        root_depth_alternation_score = 0.0

    # Check whether a legume follows a heavy-feeding crop.
    if rotation_length > 1:
        legume_after_heavy_feeder_score = np.mean([
            1.0
            if (
                rotation_crops[index].is_legume
                and rotation_crops[index - 1].heavy_feeder
            )
            else 0.0
            for index in range(1, rotation_length)
        ])
    else:
        legume_after_heavy_feeder_score = 0.0

    # Combine rotation health components.
    rotation_health_score = (
        0.35 * family_diversity_score
        + 0.35 * legume_score
        + 0.15 * min(
            root_depth_alternation_score * 2,
            1,
        )
        + 0.15 * legume_after_heavy_feeder_score
    )

    return rejection_reasons, float(rotation_health_score)


def water_check(
    crop,
    sowing_date: dt.date,
    harvest_date: dt.date,
    site: Site,
    field: FieldProfile,
    cfg: RotationConfig,
):
    """
    Evaluate whether a crop has sufficient water during its
    growing period.

    Uses a water-balance method when precipitation data is
    available, otherwise uses a soil-wetness proxy.

    Returns:
        tuple:
            passes_water_check (bool),
            rejection_reason (str),
            water_metrics (dict)
    """

    # Validate the growing period.
    if harvest_date <= sowing_date:
        raise ValueError(
            f"Harvest date must be after sowing date for {crop.crop}."
        )

    growing_days = (harvest_date - sowing_date).days

    # Calculate estimated crop water demand.
    reference_et0_mm = site.span_sum(
        "et0",
        sowing_date,
        harvest_date,
    )

    crop_water_demand_mm = reference_et0_mm * crop.kc_mean

    # Determine effective crop rooting depth.
    effective_root_depth_cm = min(
        crop.rooting_depth_m * 100,
        field.soil_depth_cm,
    )

    # Calculate available water storage in the root zone.
    available_water_storage_mm = (
        site.awc_frac * effective_root_depth_cm * 10
    )

    initial_soil_wetness = site.span_mean(
        "wet",
        sowing_date,
        sowing_date + dt.timedelta(days=10),
    )

    # Check whether the field has precipitation data.
    if site.has_precip:
        # Water-balance method.
        total_rainfall_mm = site.span_sum(
            "precip",
            sowing_date,
            harvest_date,
        )

        effective_rainfall_mm = (
            cfg.rain_eff * total_rainfall_mm
        )

        estimated_water_supply_mm = (
            available_water_storage_mm * initial_soil_wetness
            + effective_rainfall_mm
        )

        water_adequacy_ratio = (
            estimated_water_supply_mm
            / max(crop_water_demand_mm, 1e-6)
        )

        water_assessment_method = "water_balance"

    else:
        # Soil-wetness proxy method.
        average_daily_water_demand_mm = (
            crop_water_demand_mm / growing_days
        )

        required_soil_wetness = np.interp(
            average_daily_water_demand_mm,
            [2, 6],
            [cfg.min_wet_low, cfg.min_wet_high],
        )

        average_growing_season_wetness = site.span_mean(
            "wet",
            sowing_date,
            harvest_date,
        )

        water_adequacy_ratio = (
            average_growing_season_wetness
            / max(required_soil_wetness, 1e-6)
        )

        water_assessment_method = "wetness_proxy"

    # Determine whether the crop passes the water check.
    passes_water_check = (
        field.irrigation
        or water_adequacy_ratio >= cfg.water_reject_ratio
    )

    if passes_water_check:
        rejection_reason = ""

    elif water_assessment_method == "water_balance":
        rejection_reason = (
            f"{crop.crop} sown {sowing_date:%d %b}: "
            f"estimated water supply/demand ratio "
            f"{water_adequacy_ratio:.2f} "
            f"is below {cfg.water_reject_ratio:.2f} "
            f"(estimated demand: {crop_water_demand_mm:.0f} mm, "
            f"rainfed field)."
        )

    else:
        rejection_reason = (
            f"{crop.crop} sown {sowing_date:%d %b}: "
            f"soil-wetness adequacy ratio "
            f"{water_adequacy_ratio:.2f} "
            f"is below {cfg.water_reject_ratio:.2f} "
            f"(rainfall data unavailable; wetness proxy used)."
        )

    water_metrics = {
        "water_ratio": float(water_adequacy_ratio),
        "demand_mm": float(crop_water_demand_mm),
        "water_mode": water_assessment_method,
    }

    return (
        passes_water_check,
        rejection_reason,
        water_metrics,
    )


def assess_rotation(
    crops_df: pd.DataFrame,
    crop_calender_df: pd.DataFrame,
    site: Site,
    field,
    prio,
    cfg: RotationConfig,
    top_n: int = 10,
):
    """
    Assess crop rotations using multi-date sowing search and beam search.

    Each crop sequence can produce multiple possible schedules.
    Instead of accepting only the earliest sowing date, the function
    explores several valid sowing dates and retains the best partial
    schedules at each rotation stage.
    """

    WEIGHTS = priority_weight(prio)

    reject_crop = []
    accepted_crop = []

    # ---------------------------------------------------------
    # 1. PRE-SCREEN CROPS
    # ---------------------------------------------------------

    for i, crop in crops_df.iterrows():

        meta_data = []

        # Farmer exclusion
        if crop.crop in prio.exclude:
            reject_crop.append({
                "crop": crop.crop,
                "checks": "farmer_priority",
                "reasons": "excluded by farmer",
            })
            continue

        # Terrain suitability
        ok = terrain_check(field, crop)

        if not ok:
            reason = (
                f"{crop.crop} not recommended for "
                f"{field.terrain} terrain"
            )

            reject_crop.append({
                "crop": crop.crop,
                "checks": "terrain",
                "reasons": reason,
            })
            continue

        # Calendar availability
        filtered_rows = crop_calender_df[
            (
                crop_calender_df["crop"]
                .astype(str).str.strip().str.lower()
                == str(crop.crop).strip().lower()
            )
            &
            (
                crop_calender_df["aez"]
                .astype(str).str.strip().str.lower()
                == str(field.terrain).strip().lower()
            )
        ]

        if filtered_rows.empty:
            reject_crop.append({
                "crop": crop.crop,
                "checks": "season_duration",
                "reasons": (
                    f"No calendar data found for "
                    f"{crop.crop} in {field.terrain}"
                ),
            })
            continue

        # Crop duration
        parsed_gps = filtered_rows["gp_value"].apply(
            parse_gp_value
        )

        max_gp = parsed_gps.max()

        if pd.isna(max_gp) or max_gp > cfg.max_single_crop_days:
            reject_crop.append({
                "crop": crop.crop,
                "checks": "season_duration",
                "reasons": (
                    f"{crop.crop} needs ~{max_gp} days "
                    f"(maximum allowed: "
                    f"{cfg.max_single_crop_days}); "
                    "perennial/long-duration or invalid duration"
                ),
            })
            continue

        # Soil suitability
        ok, reason, _ = soil_check(
            crop,
            site,
            field,
            cfg,
        )

        if not ok:
            meta_data.append(("soil", reason))

        if meta_data:
            reject_crop.append({
                "crop": crop.crop,
                "checks": ", ".join(x[0] for x in meta_data),
                "reasons": "; ".join(x[1] for x in meta_data),
            })
        else:
            accepted_crop.append(i)

    if not accepted_crop:
        raise ValueError("No crop accepted for the rotation")

    # ---------------------------------------------------------
    # 2. PREPARE CROP POOL AND CACHES
    # ---------------------------------------------------------

    crop_pool = (
        crops_df.loc[accepted_crop]
        .reset_index(drop=True)
    )

    pool_rows = [
        crop_pool.loc[i]
        for i in crop_pool.index
    ]

    soil_cache = {
        i: soil_check(
            crop_pool.loc[i],
            site,
            field,
            cfg,
        )[2]
        for i in crop_pool.index
    }

    water_cache = {}

    rot_accpt = []
    rot_reject = []

    # Search settings
    beam_width = max(
        1,
        int(getattr(cfg, "beam_width", 100)),
    )

    date_step_days = 7

    explored_schedules = 0

    # ---------------------------------------------------------
    # 3. GENERATE CROP SEQUENCES
    # ---------------------------------------------------------

    for seq in generate_candidates(
        len(crop_pool),
        cfg.rotation_length,
        cfg.max_candidates,
        cfg.random_seed,
    ):

        rows = [
            crop_pool.loc[i]
            for i in seq
        ]

        sequence_name = " > ".join(
            str(r.crop) for r in rows
        )

        fails = []

        # -----------------------------------------------------
        # 3A. DATE-INDEPENDENT ROTATION CHECKS
        # -----------------------------------------------------

        rotation_reasons, health = rotation_check(
            rows,
            cfg,
            site._soil,
        )

        fails.extend([
            ("rotation_rules", reason)
            for reason in rotation_reasons
        ])

        names = {
            str(r.crop).strip().lower()
            for r in rows
        }

        for required_crop in prio.must_include:
            if str(required_crop).strip().lower() not in names:
                fails.append((
                    "farmer_priority",
                    f"must-include crop '{required_crop}' missing",
                ))

        food_share = float(
            np.mean([r.is_food for r in rows])
        )

        if (
            food_share < prio.min_food_share
            and prio.min_food_share > 0
        ):
            fails.append((
                "farmer_priority",
                f"food-crop share {food_share:.0%} "
                f"< required {prio.min_food_share:.0%}",
            ))

        if fails:
            rot_reject.append({
                "sequence": sequence_name,
                "checks": ", ".join(
                    sorted({x[0] for x in fails})
                ),
                "reasons": "; ".join(
                    x[1] for x in fails
                ),
            })
            continue

        # -----------------------------------------------------
        # 3B. INITIAL BEAM STATE
        # -----------------------------------------------------

        beam = [{
            "events": [],
            "t": field.start_date,
            "fallow_days": 0,
            "water_sum": 0.0,
        }]

        sequence_failures = []
        sequence_explored = 0

        # -----------------------------------------------------
        # 4. EXPAND EACH CROP THROUGH MULTIPLE SOWING DATES
        # -----------------------------------------------------

        for k, crop in enumerate(rows):

            expanded = []

            for state in beam:

                # Land becomes available after previous harvest
                if k == 0:
                    ready = state["t"]
                else:
                    ready = (
                        state["t"]
                        + dt.timedelta(
                            days=cfg.turnaround_days
                        )
                    )

                # Get all possible sowing dates in the fallow window
                sowing_options = candidate_sowing_dates(
                    field_ready_date=ready,
                    crop=crop,
                    crop_calender_df=crop_calender_df,
                    terrain_str=field.terrain,
                    max_fallow_days=cfg.max_fallow_days,
                    step_days=date_step_days,
                )

                if not sowing_options:
                    sequence_failures.append((
                        "planting_window",
                        f"{crop.crop}: no valid sowing date within "
                        f"{cfg.max_fallow_days} days after {ready}",
                    ))
                    continue

                for sow, calendar_idx in sowing_options:

                    sequence_explored += 1
                    explored_schedules += 1

                    fallow = (sow - ready).days

                    if (
                        fallow < 0
                        or fallow > cfg.max_fallow_days
                    ):
                        continue

                    # Get crop duration from this calendar row
                    gp = parse_gp_value(
                        crop_calender_df.loc[
                            calendar_idx,
                            "gp_value",
                        ]
                    )

                    if pd.isna(gp) or gp <= 0:
                        sequence_failures.append((
                            "season_duration",
                            f"{crop.crop}: invalid growing period",
                        ))
                        continue

                    harvest = sow + dt.timedelta(
                        days=int(gp)
                    )

                    # Rotation horizon check
                    total_days = (
                        harvest - field.start_date
                    ).days

                    if total_days > cfg.max_horizon_days:
                        sequence_failures.append((
                            "season_duration",
                            f"{crop.crop}: rotation exceeds "
                            f"{cfg.max_horizon_days}-day horizon",
                        ))
                        continue

                    # -----------------------------------------
                    # WATER CHECK (CACHED)
                    # -----------------------------------------

                    water_key = (
                        seq[k],
                        sow,
                        harvest,
                        calendar_idx,
                    )

                    if water_key not in water_cache:
                        water_cache[water_key] = water_check(
                            crop,
                            sow,
                            harvest,
                            site,
                            field,
                            cfg,
                        )

                    (
                        water_ok,
                        water_reason,
                        water_metrics,
                    ) = water_cache[water_key]

                    if not water_ok:
                        sequence_failures.append((
                            "water",
                            water_reason,
                        ))
                        continue

                    # -----------------------------------------
                    # NDVI
                    # -----------------------------------------

                    ndvi_value = site.span_mean(
                        "ndvi",
                        sow,
                        harvest,
                    )

                    event = {
                        "crop": crop.crop,
                        "sow": sow,
                        "harvest": harvest,
                        "fallow_d": fallow,
                        "calendar_idx": calendar_idx,
                        **water_metrics,
                        "ndvi": ndvi_value,
                    }

                    # -----------------------------------------
                    # CREATE NEW PARTIAL SCHEDULE
                    # -----------------------------------------

                    new_state = {
                        "events": state["events"] + [event],
                        "t": harvest,
                        "fallow_days": (
                            state["fallow_days"] + fallow
                        ),
                        "water_sum": (
                            state["water_sum"]
                            + min(
                                water_metrics["water_ratio"],
                                1.0,
                            )
                        ),
                    }

                    expanded.append(new_state)

            # No possible schedule survived this crop stage
            if not expanded:
                beam = []
                break

            # -------------------------------------------------
            # 5. BEAM PRUNING
            # -------------------------------------------------

            def partial_schedule_score(state):
                n_events = len(state["events"])

                average_water = (
                    state["water_sum"] / max(n_events, 1)
                )

                return (
                    average_water
                    - 0.001 * state["fallow_days"]
                )

            expanded.sort(
                key=partial_schedule_score,
                reverse=True,
            )

            beam = expanded[:beam_width]

        # -----------------------------------------------------
        # 6. NO COMPLETE SCHEDULE FOUND
        # -----------------------------------------------------

        if not beam:

            if not sequence_failures:
                sequence_failures.append((
                    "scheduling",
                    "No complete schedule survived beam search",
                ))

            unique_failures = list(
                dict.fromkeys(sequence_failures)
            )

            rot_reject.append({
                "sequence": sequence_name,
                "checks": ", ".join(
                    sorted({x[0] for x in unique_failures})
                ),
                "reasons": (
                    "; ".join(
                        x[1] for x in unique_failures[:8]
                    )
                    + f" | explored alternatives: "
                    f"{sequence_explored}"
                ),
            })

            continue

        # -----------------------------------------------------
        # 7. SCORE EVERY COMPLETE SCHEDULE IN THE BEAM
        # -----------------------------------------------------

        for state in beam:

            events = state["events"]
            final_harvest = state["t"]

            span = (
                final_harvest - field.start_date
            ).days

            if span > cfg.max_horizon_days:
                continue

            ndvi_values = [
                min(e["ndvi"] / site.ndvi_max, 1.0)
                for e in events
                if (
                    np.isfinite(e["ndvi"])
                    and site.ndvi_max > 0
                )
            ]

            # Component scores
            comp = {
                "soil_fit": float(np.mean([
                    soil_cache[i]["soil_fit"]
                    for i in seq
                ])),

                "water_fit": float(np.mean([
                    min(e["water_ratio"], 1.0)
                    for e in events
                ])),

                "timing": float(
                    sum(
                        (e["harvest"] - e["sow"]).days
                        for e in events
                    ) / max(span, 1)
                ),

                "rotation_health": health,

                "ndvi_support": (
                    float(np.mean(ndvi_values))
                    if ndvi_values
                    else np.nan
                ),

                "profit": float(np.mean([
                    r.income_index for r in rows
                ])),

                "food": food_share,
            }

            # Weighted farmer-priority score
            score = sum(
                (
                    0.0 if pd.isna(comp[key])
                    else comp[key]
                ) * weight
                for key, weight in WEIGHTS.items()
            )

            # Warnings
            warnings = []

            if (
                field.irrigation
                and any(
                    e["water_ratio"] < cfg.water_reject_ratio
                    for e in events
                )
            ):
                warnings.append(
                    "needs irrigation in at least one season"
                )

            min_data_coverage = getattr(
                cfg,
                "min_data_coverage",
                0.0,
            )

            if (
                site.ndvi_valid_share is not None
                and site.ndvi_valid_share < min_data_coverage
            ):
                warnings.append("low EO data quality")

            # Store this particular schedule
            rot_accpt.append({
                "sequence": sequence_name,
                "score": round(score, 3),
                **{
                    key: round(value, 2)
                    for key, value in comp.items()
                },
                "total_days": span,
                "fallow_days": state["fallow_days"],
                "warnings": "; ".join(warnings),
                "events": events,
            })

    # ---------------------------------------------------------
    # 8. RANK RESULTS
    # ---------------------------------------------------------

    RANKED_COLUMNS = [
        "sequence",
        "score",
        "soil_fit",
        "water_fit",
        "timing",
        "rotation_health",
        "ndvi_support",
        "profit",
        "food",
        "total_days",
        "fallow_days",
        "warnings",
        "events",
    ]

    ranked = pd.DataFrame(
        rot_accpt,
        columns=RANKED_COLUMNS,
    )

    if not ranked.empty:

        ranked = ranked.sort_values(
            ["score", "total_days", "fallow_days"],
            ascending=[False, True, True],
        ).reset_index(drop=True)

        ranked.insert(
            0,
            "rank",
            ranked.index + 1,
        )

    # ---------------------------------------------------------
    # 9. RETURN RESULTS
    # ---------------------------------------------------------

    rejected_df = pd.DataFrame(
        rot_reject,
        columns=[
            "sequence",
            "checks",
            "reasons",
        ],
    )

    feasible_sequences = (
        ranked["sequence"].nunique()
        if not ranked.empty
        else 0
    )

    return {
        "ranked": ranked,
        "top": ranked.head(top_n),
        "rejected": rejected_df,
        "crop_rejections": pd.DataFrame(reject_crop),

        "summary": {
            "candidates": feasible_sequences + len(rot_reject),
            "feasible": feasible_sequences,
            "feasible_schedules": len(rot_accpt),
            "rejected_sequences": len(rot_reject),
            "crops_screened_out": len(reject_crop),
            "crops_in_pool": len(pool_rows),
            "explored_sowing_alternatives": explored_schedules,
            "beam_width": beam_width,
            "date_step_days": date_step_days,
            "weights": {
                key: round(value, 2)
                for key, value in WEIGHTS.items()
            },
        },
    }


def run_rotation_strategy(
    final_crop_k_df: pd.DataFrame,
    crop_calendar_df: pd.DataFrame,
    site: Any,
    field_profile: FieldProfile,
    farmer_priority: FarmerPriority,
    config: RotationConfig,
    top_n: int = 20,
) -> dict[str, Any]:
    """
    Execute the crop rotation assessment algorithm.

    Parameters
    ----------
    final_crop_k_df:
        Candidate crop DataFrame produced by the earlier pipeline.

    crop_calendar_df:
        Crop calendar DataFrame.

    site:
        Site/environment information required by assess_rotation.

    field_profile:
        Field characteristics.

    farmer_priority:
        Farmer preference configuration.

    config:
        Rotation algorithm configuration.

    top_n:
        Number of top rotations to return.

    Returns
    -------
    dict:
        Contains the complete assessment result and flattened
        schedule comparison.
    """

    if final_crop_k_df.empty:
        raise ValueError("Candidate crop dataset is empty.")

    if crop_calendar_df.empty:
        raise ValueError("Crop calendar dataset is empty.")

    if top_n < 1:
        raise ValueError("top_n must be at least 1.")

    # Run the actual rotation assessment algorithm.
    result = assess_rotation(
        final_crop_k_df,
        crop_calendar_df,
        site,
        field_profile,
        farmer_priority,
        config,
        top_n=top_n,
    )

    if not isinstance(result, dict):
        raise TypeError(
            "assess_rotation() must return a dictionary."
        )

    if "top" not in result:
        raise KeyError(
            "assess_rotation() result does not contain the 'top' key."
        )

    top_results = result["top"]
    if not isinstance(top_results, pd.DataFrame):
        raise TypeError(
            "The 'top' result must be a pandas DataFrame."
        )
    
    schedule_comparison = []

    for _, row in result["top"].iterrows():
        record = {
            "rank": row["rank"],
            "sequence": row["sequence"],
            "score": row["score"],
            "water_fit": row["water_fit"],
            "total_days": row["total_days"],
            "fallow_days": row["fallow_days"]
        }

        for i, event in enumerate(row["events"], start=1):

            record[f"crop_{i}"] = event["crop"]
            record[f"sow_{i}"] = event["sow"]
            record[f"harvest_{i}"] = event["harvest"]

        schedule_comparison.append(record)

    schedule_comparison_df = pd.DataFrame(schedule_comparison)
    
    return {
        "assessment": result,
        "top": top_results,
        "schedule_comparison": len(schedule_comparison_df),
    }
