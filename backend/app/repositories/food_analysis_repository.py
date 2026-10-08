from __future__ import annotations

from datetime import datetime

from bson import ObjectId

from app.db.mongodb import MongoDatabase


class FoodAnalysisRepository:
    """User-scoped persistence for predictions and confirmed meals."""

    def __init__(self, database: MongoDatabase) -> None:
        self._collection = database.database.foodAnalyses

    async def create_prediction(self, document: dict) -> dict:
        result = await self._collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def find_for_user(self, analysis_id: str, user_id: str) -> dict | None:
        if not ObjectId.is_valid(analysis_id) or not ObjectId.is_valid(user_id):
            return None
        return await self._collection.find_one({"_id": ObjectId(analysis_id), "userId": ObjectId(user_id)})

    async def confirm(
        self, analysis_id: str, user_id: str, final_food: str, serving_multiplier: float, was_corrected: bool,
        serving_grams: float | None, nutrition_snapshot: dict | None, nutrition_status: str,
        nutrition_source: str | None, meal_balance: dict,
    ) -> dict | None:
        if not ObjectId.is_valid(analysis_id) or not ObjectId.is_valid(user_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(analysis_id), "userId": ObjectId(user_id)},
            {
                "$set": {
                    "finalConfirmedFood": final_food,
                    "wasCorrected": was_corrected,
                    "servingMultiplier": serving_multiplier,
                    "servingGrams": serving_grams,
                    "nutritionSnapshot": nutrition_snapshot,
                    "nutritionStatus": nutrition_status,
                    "nutritionSource": nutrition_source,
                    "mealBalance": meal_balance,
                    "status": "confirmed" if nutrition_snapshot else "confirmed_pending_nutrition",
                    "confirmedAt": datetime.utcnow(),
                }
            },
        )
        return await self.find_for_user(analysis_id, user_id)

    async def list_for_user(self, user_id: str, limit: int = 25) -> list[dict]:
        if not ObjectId.is_valid(user_id):
            return []
        cursor = self._collection.find({"userId": ObjectId(user_id)}).sort("createdAt", -1).limit(limit)
        return await cursor.to_list(length=limit)

    async def list_for_user_between(self, user_id: str, start: datetime, end: datetime) -> list[dict]:
        if not ObjectId.is_valid(user_id):
            return []
        cursor = self._collection.find(
            {"userId": ObjectId(user_id), "createdAt": {"$gte": start, "$lte": end}, "status": {"$in": ["confirmed", "confirmed_pending_nutrition"]}}
        )
        return await cursor.to_list(length=None)

    async def list_recent_confirmed_for_user(self, user_id: str, limit: int = 12) -> list[dict]:
        """Return a small, user-scoped context window for conversational answers."""
        if not ObjectId.is_valid(user_id):
            return []
        safe_limit = max(1, min(limit, 20))
        cursor = self._collection.find(
            {"userId": ObjectId(user_id), "status": {"$in": ["confirmed", "confirmed_pending_nutrition"]}}
        ).sort("createdAt", -1).limit(safe_limit)
        return await cursor.to_list(length=safe_limit)
