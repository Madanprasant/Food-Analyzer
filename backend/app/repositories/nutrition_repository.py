from __future__ import annotations

from app.db.mongodb import MongoDatabase


class NutritionRepository:
    def __init__(self, database: MongoDatabase) -> None:
        self._collection = database.database.nutritionFoods

    async def get_by_model_class(self, model_class: str) -> dict | None:
        return await self._collection.find_one({"modelClass": model_class})

    async def get_by_canonical_food(self, canonical_food: str) -> dict | None:
        return await self._collection.find_one({"canonicalFood": canonical_food})

    async def upsert_many(self, records: list[dict]) -> int:
        changed = 0
        for record in records:
            result = await self._collection.replace_one({"modelClass": record["modelClass"]}, record, upsert=True)
            changed += int(result.modified_count > 0 or result.upserted_id is not None)
        return changed
