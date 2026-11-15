from dataclasses import dataclass, field
from typing import List

@dataclass
class FarmerPriority():
    """
        Farmer priority on the scale between 0-1 with normalized as .5. And only one number after decimal \n
        0.0 -> Not important \n
        0.3 -> Low importantance \n
        0.5 -> Medium importance \n
        0.8 -> High importance \n
        1.0 -> Extremely important \n

        Args:
            profit: float
            food_security: float
            soil_health: float
            water_saving: float
            low_risk: float
    """
    profit: float = 0.5
    food_security: float = 0.5
    soil_health: float = 0.5
    water_saving: float = 0.5
    low_risk: float = 0.5
    must_include: List[str] = field(default_factory=list)   # crop names
    exclude: List[str] = field(default_factory=list)
    min_food_share: float = 0.0

    @staticmethod
    def _count_decimals(value: float) -> int:
        str_value = str(value)
        if "." in str_value:
            # Split by '.' and count characters on the right
            return len(str_value.split(".")[1])
        return 0

    def __post_init__(self):
        _preferences = {
            "profit": self.profit,
            "food_security": self.food_security,
            "soil_health": self.soil_health,
            "water_saving": self.water_saving,
            "low_risk": self.low_risk
        }
        for name, value in _preferences.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"Priority '{name}' must be numeric."
                )
            
            if not (0 <= value <= 1):
                raise ValueError(
                    f"{name} must be between 0 and 1. Got {value}"
                )

        if not (0 <= self.min_food_share <= 1 ):
            raise ValueError(
                f"min_food_share must be between 0 and 1 "
                f"Got {self.min_food_share}"
            )