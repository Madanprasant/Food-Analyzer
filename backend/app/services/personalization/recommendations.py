from __future__ import annotations

from collections import Counter
from datetime import datetime, time, timezone

from app.services.nutrition.calculator import aggregate_snapshots


# Approximate serving information is shown only to make a suggestion easy to compare.
# It is separate from the sourced values saved for a user's meals.
_FOOD_OPTIONS = {
    "lighter": {"food": "Vegetable soup with a small roti", "nutrition": {"calories_kcal": 170, "protein_g": 6, "carbohydrate_g": 29, "fat_g": 3, "fiber_g": 5}},
    "protein": {"food": "Moong dal chilla with vegetables", "nutrition": {"calories_kcal": 220, "protein_g": 12, "carbohydrate_g": 31, "fat_g": 5, "fiber_g": 5}},
    "fiber": {"food": "Mixed vegetable salad with chana", "nutrition": {"calories_kcal": 210, "protein_g": 9, "carbohydrate_g": 34, "fat_g": 4, "fiber_g": 9}},
    "balance": {"food": "Dal, seasonal vegetables, and one roti", "nutrition": {"calories_kcal": 320, "protein_g": 15, "carbohydrate_g": 49, "fat_g": 7, "fiber_g": 8}},
}
_LIGHTER_ALTERNATIVES = {
    "biryani": "Vegetable pulao with raita", "butter chicken": "Tandoori chicken with salad",
    "chole bhature": "Chole with roti and salad", "fried rice": "Vegetable rice with extra vegetables",
    "pizza": "Vegetable whole-wheat wrap", "samosa": "Baked vegetable cutlet",
}


def _snapshot(document: dict) -> dict | None:
    return document.get("nutritionSnapshot") or document.get("nutrition_snapshot")


def _confirmed(documents: list[dict]) -> list[dict]:
    return [item for item in documents if item.get("status") in {"confirmed", "confirmed_pending_nutrition"}]


def _food_name(document: dict) -> str:
    return str(document.get("finalConfirmedFood") or document.get("final_food") or document.get("originalPrediction", {}).get("food") or document.get("predicted_food") or "").strip()


def _created_at(document: dict) -> datetime | None:
    value = document.get("createdAt") or document.get("created_at")
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return None


def _is_today(document: dict, now: datetime) -> bool:
    created_at = _created_at(document)
    start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    return created_at is not None and created_at >= start


def build_recommendations(documents: list[dict], profile: dict, now: datetime | None = None) -> list[dict]:
    """Create deterministic, non-medical suggestions from caller-provided user history."""
    now = now or datetime.now(timezone.utc)
    now = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
    history = _confirmed(documents)
    if not history:
        return [{"title": "Log a meal to personalize suggestions", "reason": "Add a confirmed meal with nutrition information and this space will use your own history.", "food": "Your next usual meal", "type": "start_tracking", "nutrition": None}]

    today = [item for item in history if _is_today(item, now)]
    today_totals = aggregate_snapshots(today)["totals"]
    calorie_target = profile.get("calorieTarget") or profile.get("calorie_target")
    protein_target = profile.get("proteinTargetG") or profile.get("protein_target_g")
    suggestions: list[dict] = []
    used_types: set[str] = set()

    def add(option_type: str, title: str, reason: str, *, food: str | None = None, nutrition: dict | None = None) -> None:
        if option_type in used_types:
            return
        choice = _FOOD_OPTIONS.get(option_type)
        suggestions.append({
            "title": title,
            "reason": reason,
            "food": food or choice["food"],
            "type": option_type,
            "nutrition": nutrition if nutrition is not None else (choice["nutrition"] if choice else None),
        })
        used_types.add(option_type)

    calories = today_totals.get("calories_kcal")
    if calorie_target and calories is not None and calories >= calorie_target * 0.8:
        add("lighter", "Choose a lighter next meal", f"Your sourced meals are at {round(calories / calorie_target * 100)}% of your daily calorie target, so a lighter option may fit better today.")

    protein = today_totals.get("protein_g")
    if protein_target and protein is not None and protein < protein_target * 0.5:
        add("protein", "Add a protein-rich food", f"Your sourced meals provide {round(protein / protein_target * 100)}% of your daily protein target so far today.")

    fiber = today_totals.get("fiber_g")
    if fiber is not None and fiber < 14:
        add("fiber", "Include a fiber-rich side", f"Your logged meals contain {round(fiber, 1)} g of fiber today; vegetables, legumes, and fruit can help add variety.")

    carbohydrate = today_totals.get("carbohydrate_g")
    fat = today_totals.get("fat_g")
    macro_note = None
    if calories and carbohydrate is not None and carbohydrate * 4 / calories >= 0.7:
        macro_note = "Your available totals lean heavily toward carbohydrates today."
    elif calories and fat is not None and fat * 9 / calories >= 0.4:
        macro_note = "Your available totals are relatively high in fat today."
    scores = [item.get("mealBalance", {}).get("score") for item in history]
    valid_scores = [score for score in scores if isinstance(score, (int, float))]
    if (valid_scores and sum(valid_scores) / len(valid_scores) < 75) or macro_note:
        reason = macro_note or "Your recent meal balance scores suggest pairing a protein source with vegetables and a staple food more often."
        add("balance", "Build a more balanced plate", reason)

    foods = [name for name in (_food_name(item) for item in history) if name]
    repeated_food, count = next(((food, value) for food, value in Counter(food.lower() for food in foods).most_common() if value >= 3), (None, 0))
    if repeated_food:
        repeated_meals = [item for item in history if _food_name(item).lower() == repeated_food]
        values = [(_snapshot(item) or {}).get("calories_kcal") for item in repeated_meals]
        sourced = [value for value in values if isinstance(value, (int, float))]
        if not sourced or sum(sourced) / len(sourced) >= 250:
            add("variety", "Try a lighter variation", f"You logged {repeated_food.title()} {count} times recently. A different preparation can add variety while keeping the meal familiar.", food=_LIGHTER_ALTERNATIVES.get(repeated_food, "Dal, seasonal vegetables, and one roti"), nutrition=None)

    if not suggestions:
        add("next_meal", "A balanced next-meal idea", "Your available meal data does not show a strong gap today. A balanced plate is a practical next choice.", food=_FOOD_OPTIONS["balance"]["food"], nutrition=_FOOD_OPTIONS["balance"]["nutrition"])
    return suggestions[:4]
