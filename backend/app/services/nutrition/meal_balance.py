from __future__ import annotations


def calculate_meal_balance(nutrition: dict | None, profile: dict) -> dict:
    """Transparent support score, not medical advice.

    Starts at 100. Calorie share above 45% of a daily target loses up to 35 points;
    protein below 25% of daily protein target loses up to 25; fiber below 4 g loses
    10. It returns insufficient data whenever referenced sourced values are absent.
    """
    calorie_target = profile.get("calorieTarget")
    protein_target = profile.get("proteinTargetG")
    if not nutrition or nutrition.get("calories_kcal") is None or not calorie_target:
        return {"status": "insufficient_data", "score": None, "explanation": "A sourced meal nutrition value and daily calorie target are required."}
    score = 100
    notes: list[str] = []
    calorie_share = nutrition["calories_kcal"] / calorie_target
    if calorie_share > 0.45:
        penalty = min(35, round((calorie_share - 0.45) * 100))
        score -= penalty
        notes.append("This serving uses a large share of the daily calorie target.")
    if protein_target and nutrition.get("protein_g") is not None:
        protein_share = nutrition["protein_g"] / protein_target
        if protein_share < 0.25:
            score -= min(25, round((0.25 - protein_share) * 100))
            notes.append("Protein is below one quarter of the daily target.")
    if nutrition.get("fiber_g") is not None and nutrition["fiber_g"] < 4:
        score -= 10
        notes.append("Fiber is below the 4 g meal-support threshold.")
    return {
        "status": "available",
        "score": max(0, min(100, score)),
        "explanation": " ".join(notes) or "This meal fits the available calorie, protein, and fiber checks.",
        "formula_version": "meal-balance-v1",
    }
