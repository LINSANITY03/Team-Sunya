from schemas.rotation import (
    RotationRequest,
    RotationResponse,
)


class RotationService:
    def __init__(self, engine):
        self.engine = engine

    def recommend(
        self,
        request: RotationRequest,
    ) -> RotationResponse:

        # Convert API request into engine parameters
        priorities = request.farmer_priorities.model_dump()

        # Execute the actual rotation algorithm
        result = self.engine.get_top_k_rotations(
            latitude=request.location.latitude,
            longitude=request.location.longitude,
            top_k=request.top_k,
            planning_years=request.planning_years,
            farmer_priorities=priorities,
            constraints=request.constraints.model_dump(),
        )

        # Convert algorithm results into API response
        return RotationResponse(
            status="success",
            total_candidates=result["total_candidates"],
            total_valid_rotations=result["total_valid_rotations"],
            returned=len(result["rotations"]),
            rotations=result["rotations"],
        )
