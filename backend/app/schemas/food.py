from datetime import datetime

from pydantic import BaseModel, Field


class TopPredictionResponse(BaseModel):
    food: str
    confidence: float


class AnalyzeFoodResponse(BaseModel):
    analysis_id: str
    predicted_food: str
    confidence: float
    top_k: list[TopPredictionResponse]
    low_confidence: bool
    confidence_threshold: float
    model_name: str
    model_version: str
    nutrition_status: str = "Nutrition database integration pending."


class ConfirmFoodRequest(BaseModel):
    analysis_id: str
    final_food: str = Field(min_length=1, max_length=100)
    serving_multiplier: float = Field(default=1.0, ge=0.25, le=4.0)
    serving_grams: float | None = Field(default=None, gt=0, le=3000)


class ConfirmFoodResponse(BaseModel):
    analysis_id: str
    final_food: str
    was_corrected: bool
    serving_multiplier: float
    status: str
    nutrition_status: str
    nutrition_snapshot: dict | None = None
    meal_balance: dict


class FoodHistoryItem(BaseModel):
    analysis_id: str
    created_at: datetime
    predicted_food: str
    confidence: float
    final_food: str | None = None
    was_corrected: bool | None = None
    status: str
