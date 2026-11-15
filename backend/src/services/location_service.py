import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point
from functools import lru_cache

BASE_DIR = Path(__file__).resolve().parents[2]
NEPAL_GEO_DIR = BASE_DIR / "data" / "Country"
NEPAL_GEO_PATH = NEPAL_GEO_DIR / "nepal.geojson"


@lru_cache(maxsize=1)
def get_nepal_boundary():
    """Load Nepal's boundary once and reuse it."""

    if not NEPAL_GEO_PATH.exists():
        raise FileNotFoundError(
            f"Nepal GeoJSON not found: {NEPAL_GEO_PATH}"
        )

    nepal_gdf = gpd.read_file(NEPAL_GEO_PATH)

    if nepal_gdf.empty:
        raise ValueError("Nepal GeoJSON contains no geometries.")

    if nepal_gdf.crs is not None and nepal_gdf.crs.to_epsg() != 4326:
        nepal_gdf = nepal_gdf.to_crs(epsg=4326)

    return nepal_gdf.geometry.union_all()


def is_inside_nepal(lat: float, lon: float) -> bool:
    """Check whether coordinates fall within Nepal."""

    nepal_boundary = get_nepal_boundary()
    point = Point(lon, lat)

    return (
        nepal_boundary.contains(point)
        or nepal_boundary.touches(point)
    )