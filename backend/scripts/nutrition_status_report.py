"""Print a traceability-focused status summary for all imported nutrition records."""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

from pymongo import MongoClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402


def main() -> None:
    settings = get_settings()
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI is required.")
    client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=10000)
    records = list(client[settings.database_name].nutritionFoods.find({}, {"_id": 0, "status": 1, "mappingStatus": 1}))
    if len(records) != 239:
        raise SystemExit(f"Expected 239 imported records; found {len(records)}.")
    status_counts = Counter(record["status"] for record in records)
    mapping_counts = Counter(record["mappingStatus"] for record in records)
    print("PLATESIGNAL nutrition status report")
    print(f"Total model classes: {len(records)}")
    print(f"Verified/direct IFCT: {status_counts['verified']}")
    print(f"Recipe definition pending: {mapping_counts['IFCT_RECIPE']}")
    print(f"Secondary source pending: {mapping_counts['SECONDARY_SOURCE_REQUIRED']}")
    print(f"Total nutrition pending: {status_counts['nutrition_pending']}")
    client.close()


if __name__ == "__main__":
    main()
