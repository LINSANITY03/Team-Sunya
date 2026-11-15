
from sqlalchemy.orm import Session

from database.models import RecommendationData


class RecommendationDataRepository:
    """Retrieve external datasets saved for a recommendation job."""

    REQUIRED_SOURCES = (
        "NASA_POWER",
        "ELEVATION",
        "SOILGRIDS",
        "MODIS",
    )

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_all_sources(self, recommendation_id: str) -> dict:
        records = (
            self.db.query(RecommendationData)
            .filter(
                RecommendationData.recommendation_id == recommendation_id
            )
            .all()
        )

        sources = {
            record.source: {
                "status": record.status,
                "data": record.data,
                "error_message": record.error_message,
            }
            for record in records
        }

        missing = set(self.REQUIRED_SOURCES) - set(sources)

        if missing:
            raise ValueError(
                f"Missing data source records: {sorted(missing)}"
            )

        return sources

    def get_successful_sources(self, recommendation_id: str) -> dict:
        """Return source payloads, rejecting failed or incomplete sources."""

        sources = self.get_all_sources(recommendation_id)

        failed = {
            name: source["error_message"]
            for name, source in sources.items()
            if source["status"] != "SUCCESS"
        }

        if failed:
            raise ValueError(
                f"Required data sources are not successful: {failed}"
            )

        return {
            name: source["data"]
            for name, source in sources.items()
        }
