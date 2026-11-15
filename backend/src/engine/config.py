from dataclasses import dataclass, field
from typing import Tuple, Dict

@dataclass
class RotationConfig:
    # --- candidate generation
    rotation_length: int = 3              # number of crop cycles in the rotation
    max_candidates: int = 50_000          # random-sample if the full product is larger
    random_seed: int = 27
    # --- timing
    turnaround_days: int = 10           # land prep between harvest and next sowing
    max_fallow_days: int = 120            # longest acceptable idle gap between crops
    max_horizon_days: int = 800           # whole rotation must finish within this
    max_single_crop_days: int = 300       # longer = perennial / not rotatable
    harvest_mismatch_tol_days: int = 20   # data-quality flag only
    # --- water
    rain_eff: float = 0.8                # effective-rain fraction (only if precip column exists)
    min_wet_low: float = 0.25             # required mean profile wetness at low demand (2 mm/d)
    min_wet_high: float = 0.55            # ... at high demand (6 mm/d)
    water_reject_ratio: float = 0.20      # rainfed: reject if supply/demand ratio below this
    rs_unit: str = "kWh"                  # "kWh" (kWh/m2/day) or "MJ" (MJ/m2/day)
    # --- soil
    bd_reject: float = 1.75               # bulk density (kg/dm3) at/above which roots are blocked
    clay_max_root_crops: float = 55.0     # % clay: reject tuber/root crops above this
    min_soil_depth_ratio: float = 0.5     # soil depth must be >= this fraction of rooting depth
    n_ok_g_per_kg: float = 2.0            # soil N above this = little need for N-fixers
    # --- rotation rules
    cyclic: bool = True                   # rotation repeats, so last->first also counts for family gap
    default_family_gap: int = 2           # same family must be >= this many cycles apart
    family_gap_overrides: Dict[str, int] = field(default_factory=lambda: {
        "Solanaceae": 3, "Brassicaceae": 3, "Fabaceae": 2})
    require_legume: bool = False           # at least one legume / green manure in the rotation

    def __post_init__(self) -> None:
        """Validate rotation configuration."""

        if self.max_candidates < 1:
            raise ValueError("max_candidates must be at least 1.")

        if self.max_horizon_days < 1:
            raise ValueError("max_horizon_days must be positive.")

        if self.max_single_crop_days < 1:
            raise ValueError(
                "max_single_crop_days must be positive."
            )

        if self.max_fallow_days < 0:
            raise ValueError(
                "max_fallow_days cannot be negative."
            )

        if self.default_family_gap < 0:
            raise ValueError(
                "default_family_gap cannot be negative."
            )

        if self.harvest_mismatch_tol_days < 0:
            raise ValueError(
                "harvest_mismatch_tol_days cannot be negative."
            )

        if self.turnaround_days < 0:
            raise ValueError(
                "turnaround_days cannot be negative."
            )

        if self.rotation_length < 1:
            raise ValueError(
                "rotation_length must be at least 1."
            )

