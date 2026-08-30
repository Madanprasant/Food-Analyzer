from pathlib import Path

from app.services.nutrition.calculator import aggregate_snapshots, calculate_serving
from app.services.nutrition.seed import load_normalized_seed


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def test_seed_has_239_unique_model_classes_and_pending_values_are_null() -> None:
    records = load_normalized_seed(PROJECT_ROOT / "backend" / "data" / "platesignal_nutrition_seed.json")
    assert len(records) == 239
    assert len({record["modelClass"] for record in records}) == 239
    pending = next(record for record in records if record["modelClass"] == "aloo paratha")
    assert pending["status"] == "nutrition_pending"
    assert all(value is None for value in pending["nutrients"].values())


def test_ifct_energy_is_preserved_and_kcal_conversion_and_serving_are_deterministic() -> None:
    records = load_normalized_seed(PROJECT_ROOT / "backend" / "data" / "platesignal_nutrition_seed.json")
    apple = next(record for record in records if record["modelClass"] == "apple")
    assert apple["nutrients"]["energy_kj"] == 261.0
    assert apple["nutrients"]["calories_kcal"] == 62.38
    serving = calculate_serving(apple, 120)
    assert serving["calories_kcal"] == 74.86
    assert calculate_serving(next(record for record in records if record["modelClass"] == "aloo paratha"), 120) is None


def test_aggregation_keeps_missing_nutrition_visible_not_zero() -> None:
    aggregate = aggregate_snapshots([
        {"nutritionSnapshot": {"calories_kcal": 100, "protein_g": 4, "energy_kj": 418.4}},
        {"nutritionSnapshot": None},
    ])
    assert aggregate["totals"]["calories_kcal"] == 100
    assert aggregate["totals"]["fat_g"] is None
    assert aggregate["nutrition_unavailable_meal_count"] == 1
