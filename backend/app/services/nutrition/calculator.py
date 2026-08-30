from __future__ import annotations

from typing import Any


NUTRIENT_FIELDS = ("calories_kcal", "energy_kj", "protein_g", "carbohydrate_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")


def calculate_serving(record: dict, serving_grams: float | None) -> dict | None:
    """Scale only sourced per-100g nutrients; pending data remains pending, never zero."""
    if record.get("status") not in {"verified", "recipe_based", "secondary_source"}:
        return None
    if record.get("nutritionBasis") != "per_100g" or serving_grams is None:
        return None
    multiplier = serving_grams / 100
    nutrients = record.get("nutrients", {})
    return {
        key: round(nutrients[key] * multiplier, 2) if nutrients.get(key) is not None else None
        for key in NUTRIENT_FIELDS
    }


def aggregate_snapshots(documents: list[dict]) -> dict[str, Any]:
    """Aggregate only nutrients present in confirmed snapshots; missing remains visible."""
    totals: dict[str, float | None] = {field: None for field in NUTRIENT_FIELDS}
    meals_with_nutrition = 0
    unavailable_meals = 0
    for document in documents:
        snapshot = document.get("nutritionSnapshot")
        if not snapshot:
            unavailable_meals += 1
            continue
        meals_with_nutrition += 1
        for field in NUTRIENT_FIELDS:
            value = snapshot.get(field)
            if value is not None:
                totals[field] = round((totals[field] or 0) + value, 2)
    return {
        "totals": totals,
        "logged_meal_count": len(documents),
        "meals_with_nutrition": meals_with_nutrition,
        "nutrition_unavailable_meal_count": unavailable_meals,
    }
