from typing import Literal

from pydantic import BaseModel

from app.schemas.nutrition import NutrientValues


class RecommendationItem(BaseModel):
    """An explainable food suggestion, not clinical advice."""

    title: str
    reason: str
    food: str
    type: Literal["lighter", "protein", "fiber", "balance", "variety", "next_meal", "start_tracking"]
    nutrition: NutrientValues | None = None


class RecommendationsResponse(BaseModel):
    recommendations: list[RecommendationItem]
    period_days: int
    note: str = "Suggestions use only your logged meals and available nutrition data. They are not medical advice."
