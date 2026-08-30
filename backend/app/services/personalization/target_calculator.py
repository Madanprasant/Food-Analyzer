from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuggestedTargets:
    calories: int
    protein_grams: int


def suggest_starting_targets(
    *, age: int, height_cm: float, weight_kg: float, activity_level: str, fitness_goal: str, sex_for_estimation: str
) -> SuggestedTargets:
    """Return transparent starting targets, not medical advice or a diagnosis."""
    base_offset = {"female": -161, "male": 5, "prefer_not_to_say": -78}.get(sex_for_estimation, -78)
    resting_calories = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + base_offset
    activity_factor = {"sedentary": 1.2, "lightly_active": 1.375, "moderately_active": 1.55, "very_active": 1.725}.get(activity_level, 1.55)
    goal_adjustment = {"weight_loss": -300, "weight_maintenance": 0, "muscle_gain": 250, "general_healthy_eating": 0}.get(fitness_goal, 0)
    calories = max(1200, round(((resting_calories * activity_factor) + goal_adjustment) / 25) * 25)
    protein_per_kg = {"weight_loss": 1.2, "weight_maintenance": 1.0, "muscle_gain": 1.6, "general_healthy_eating": 0.8}.get(fitness_goal, 0.8)
    return SuggestedTargets(calories=calories, protein_grams=round(weight_kg * protein_per_kg))
