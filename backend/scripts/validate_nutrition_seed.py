"""Validate the nutrition seed before import; no database writes are made."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.nutrition.seed import load_normalized_seed  # noqa: E402


def main() -> None:
    settings = get_settings()
    records = load_normalized_seed(settings.nutrition_seed_path)
    mapping_path = settings.nutrition_seed_path.parent / "nutrition_mapping.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))["mappings"]
    model_classes = {record["modelClass"] for record in records}
    assert len(model_classes) == 239, "Expected 239 unique nutrition model classes."
    assert model_classes == {record["model_class"] for record in mapping}, "Mapping and seed classes differ."
    for record in records:
        if record["status"] != "nutrition_pending":
            assert record["source"] and record["sourceFoodCode"], "Sourced records need source and IFCT code."
            assert record["nutritionBasis"] == "per_100g", "Direct IFCT records must be per 100 g."
            assert record["nutrients"]["energy_kj"] is not None, "Source energy cannot be missing."
        else:
            assert all(value is None for value in record["nutrients"].values()), "Pending nutrients must be null."
            assert not record["recipeComponents"], "Seed has no documented recipe components yet."
    print("Nutrition seed validation passed: 239 classes, source provenance, pending/null policy, and unique model classes are valid.")


if __name__ == "__main__":
    main()
