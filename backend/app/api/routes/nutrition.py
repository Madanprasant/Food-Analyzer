from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_current_user, get_database
from app.repositories.food_analysis_repository import FoodAnalysisRepository
from app.repositories.nutrition_repository import NutritionRepository
from app.schemas.nutrition import (
    NutritionFoodResponse, NutritionTotalsResponse, NutrientValues, ServingNutritionRequest, ServingNutritionResponse,
)
from app.services.nutrition.calculator import aggregate_snapshots, calculate_serving

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


def serialize_food(record: dict) -> NutritionFoodResponse:
    return NutritionFoodResponse(
        model_class=record["modelClass"], canonical_food=record["canonicalFood"], status=record["status"],
        source=record.get("source"), source_reference=record.get("sourceReference"),
        source_food_code=record.get("sourceFoodCode"), nutrition_basis=record.get("nutritionBasis"),
        serving_size_g=record.get("servingSizeG"), nutrients_per_basis=record.get("nutrients", {}),
        notes=record.get("notes", ""), calculation_method=record.get("calculationMethod"),
    )


async def resolve_food(food: str, database: MongoDatabase) -> dict:
    repository = NutritionRepository(database)
    record = await repository.get_by_model_class(food) or await repository.get_by_canonical_food(food)
    if not record:
        raise HTTPException(status_code=404, detail="Nutrition record was not found.")
    return record


@router.get("/{food}", response_model=NutritionFoodResponse)
async def get_nutrition(food: str, database: MongoDatabase = Depends(get_database)) -> NutritionFoodResponse:
    try:
        return serialize_food(await resolve_food(food, database))
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/{food}/serving", response_model=ServingNutritionResponse)
async def calculate_serving_nutrition(
    food: str, payload: ServingNutritionRequest, database: MongoDatabase = Depends(get_database)
) -> ServingNutritionResponse:
    try:
        record = await resolve_food(food, database)
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    nutrients = calculate_serving(record, payload.serving_grams)
    return ServingNutritionResponse(
        food=serialize_food(record), serving_grams=payload.serving_grams, nutrients=nutrients,
        status="available" if nutrients else record["status"],
    )


async def totals_for_days(user: dict, database: MongoDatabase, days: int) -> NutritionTotalsResponse:
    end = datetime.now(timezone.utc)
    start = datetime.combine((end - timedelta(days=days - 1)).date(), time.min, tzinfo=timezone.utc)
    documents = await FoodAnalysisRepository(database).list_for_user_between(str(user["_id"]), start, end)
    aggregate = aggregate_snapshots(documents)
    return NutritionTotalsResponse(period_start=start.date().isoformat(), period_end=end.date().isoformat(), **aggregate)


@router.get("/totals/daily", response_model=NutritionTotalsResponse)
async def daily_totals(user: dict = Depends(get_current_user), database: MongoDatabase = Depends(get_database)) -> NutritionTotalsResponse:
    try:
        return await totals_for_days(user, database, 1)
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.get("/totals/weekly", response_model=NutritionTotalsResponse)
async def weekly_totals(user: dict = Depends(get_current_user), database: MongoDatabase = Depends(get_database)) -> NutritionTotalsResponse:
    try:
        return await totals_for_days(user, database, 7)
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
