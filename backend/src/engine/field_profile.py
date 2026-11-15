from dataclasses import dataclass
import datetime as dt
import numpy as np

@dataclass
class FieldProfile:
    """
        Defines the physical and operational characterisitics of the land.
    """
    _VALID_TERRAINS = ["Terai", "Hill", "Mountain"]
    field_id: str = "field_001"
    terrain: str = "Terai"
    irrigation: bool = False
    soil_depth_cm: float = 100.0
    start_date: dt.date = dt.date(2026, 11, 1)

    def __post_init__(self):
        if self.terrain not in self._VALID_TERRAINS:
            raise ValueError(
                    f"Invalid terrain: {self.terrain}."
                    f"Choose from {self._VALID_TERRAINS}")
        if not 0 < self.soil_depth_cm <= 200:      # the old check let 0 and negative depths through
            raise ValueError(f"soil_depth_cm must be > 0 and <= 200. Got {self.soil_depth_cm}")
        if not isinstance(self.irrigation, (bool, np.bool_)):
            raise TypeError(f"irrigation must be True/False. Got {self.irrigation!r}")
        if isinstance(self.start_date, dt.datetime) or not isinstance(self.start_date, dt.date):
            raise TypeError("start_date must be a datetime.date")