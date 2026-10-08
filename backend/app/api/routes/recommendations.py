from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_current_user, get_database
from app.repositories.food_analysis_repository import FoodAnalysisRepository
from app.schemas.recommendation import RecommendationItem, RecommendationsResponse
from app.services.personalization.recommendations import build_recommendations

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", response_model=RecommendationsResponse)
async def get_recommendations(user: dict = Depends(get_current_user), database: MongoDatabase = Depends(get_database)) -> RecommendationsResponse:
    """Return suggestions based only on the current user's last 30 days of meals."""
    now = datetime.now(timezone.utc)
    try:
        history = await FoodAnalysisRepository(database).list_for_user_between(str(user["_id"]), now - timedelta(days=30), now)
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    recommendations = build_recommendations(history, user.get("profile", {}), now)
    return RecommendationsResponse(recommendations=[RecommendationItem.model_validate(item) for item in recommendations], period_days=30)
