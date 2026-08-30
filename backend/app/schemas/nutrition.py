from typing import Literal

from pydantic import BaseModel, Field


class NutrientValues(BaseModel):
    calories_kcal: float | None = None
    energy_kj: float | None = None
    protein_g: float | None = None
    carbohydrate_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    sugar_g: float | None = None
    sodium_mg: float | None = None


class NutritionFoodResponse(BaseModel):
    model_class: str
    canonical_food: str
    status: Literal["verified", "recipe_based", "secondary_source", "nutrition_pending"]
    source: str | None = None
    source_reference: str | None = None
    source_food_code: str | None = None
    nutrition_basis: str | None = None
    serving_size_g: float | None = None
    nutrients_per_basis: NutrientValues
    notes: str
    calculation_method: str | None = None


class ServingNutritionRequest(BaseModel):
    serving_grams: float = Field(gt=0, le=3000)


class ServingNutritionResponse(BaseModel):
    food: NutritionFoodResponse
    serving_grams: float
    nutrients: NutrientValues | None
    status: str


class NutritionTotalsResponse(BaseModel):
    period_start: str
    period_end: str
    totals: NutrientValues
    logged_meal_count: int
    meals_with_nutrition: int
    nutrition_unavailable_meal_count: int
