from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path


IFCT_SOURCE = "ICMR-NIN Indian Food Composition Tables (IFCT) 2017"
IFCT_REFERENCE = "Supplied IFCT 2017 machine-readable index.csv"


def _safe_number(value: object) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(result) or math.isinf(result) else result


def normalize_seed_record(record: dict) -> dict:
    """Normalize supplied seed data without filling any missing nutrition fact.

    IFCT energy supplied here is kilojoules per 100 g edible portion. `energy_kj`
    preserves the reported source value; kcal is a deterministic unit conversion.
    """
    direct = record["status"] == "IFCT_DIRECT" and record.get("verified") is True
    energy_kj = _safe_number(record.get("calories_kcal")) if direct else None
    nutrients = {
        "calories_kcal": round(energy_kj / 4.184, 2) if energy_kj is not None else None,
        "energy_kj": energy_kj,
        "protein_g": _safe_number(record.get("protein_g")) if direct else None,
        "carbohydrate_g": _safe_number(record.get("carbohydrate_g")) if direct else None,
        "fat_g": _safe_number(record.get("fat_g")) if direct else None,
        "fiber_g": _safe_number(record.get("fiber_g")) if direct else None,
        "sugar_g": None,
        "sodium_mg": None,
    }
    return {
        "modelClass": record["model_class"],
        "canonicalFood": record["canonical_food"],
        "aliases": [],
        "status": "verified" if direct else "nutrition_pending",
        "source": IFCT_SOURCE if direct else None,
        "sourceReference": IFCT_REFERENCE if direct else None,
        "sourceFoodCode": record.get("source_food_code") if direct else None,
        "nutritionBasis": "per_100g" if direct else None,
        "servingSizeG": None,
        "nutrients": nutrients,
        "micronutrients": {},
        "recipeComponents": [],
        "confidence": "high" if direct else "pending",
        "notes": record.get("notes", ""),
        "mappingStatus": record["status"],
        "calculationMethod": "kcal = supplied IFCT energy (kJ) / 4.184" if direct else None,
        "seededAt": datetime.now(timezone.utc),
    }


def load_normalized_seed(path: Path) -> list[dict]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    records = raw.get("records")
    if not isinstance(records, list) or len(records) != 239:
        raise ValueError("Nutrition seed must contain exactly 239 records.")
    normalized = [normalize_seed_record(record) for record in records]
    names = [record["modelClass"] for record in normalized]
    if len(set(names)) != len(names):
        raise ValueError("Nutrition seed contains duplicate model classes.")
    return normalized
