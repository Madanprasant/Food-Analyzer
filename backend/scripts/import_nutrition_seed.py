"""Idempotently load supplied, traceable nutrition seed records into MongoDB.

Run from backend: python scripts/import_nutrition_seed.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from pymongo import MongoClient, ReplaceOne

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.services.nutrition.seed import load_normalized_seed  # noqa: E402


def main() -> None:
    settings = get_settings()
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI is required before importing the nutrition seed.")
    records = load_normalized_seed(settings.nutrition_seed_path)
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=10000)
    collection = client[settings.database_name].nutritionFoods
    result = collection.bulk_write(
        [ReplaceOne({"modelClass": record["modelClass"]}, record, upsert=True) for record in records], ordered=False
    )
    collection.create_index("modelClass", unique=True, name="nutrition_model_class_unique")
    collection.create_index("canonicalFood", name="nutrition_canonical_food")
    print(f"Nutrition seed complete: {len(records)} records; {result.upserted_count} inserted; {result.modified_count} updated.")
    client.close()


if __name__ == "__main__":
    main()
