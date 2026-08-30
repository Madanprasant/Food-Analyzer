from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection

from app.db.mongodb import MongoDatabase


class ModelRepository:
    def __init__(self, database: MongoDatabase) -> None:
        self._collection: AsyncIOMotorCollection = database.database.modelVersions

    async def ensure_baseline(self, document: dict) -> None:
        await self._collection.update_one(
            {"modelFilePath": document["modelFilePath"], "version": document["version"]},
            {"$setOnInsert": document}, upsert=True,
        )

    async def list_all(self) -> list[dict]:
        return await self._collection.find({}).sort("uploadedAt", -1).to_list(length=250)

    async def find_by_id(self, model_id: str) -> dict | None:
        if not ObjectId.is_valid(model_id):
            return None
        return await self._collection.find_one({"_id": ObjectId(model_id)})

    async def create(self, document: dict) -> dict:
        result = await self._collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    async def set_active(self, model_id: str, activated_by: ObjectId, now: datetime) -> dict | None:
        if not ObjectId.is_valid(model_id):
            return None
        candidate_id = ObjectId(model_id)
        await self._collection.update_many(
            {"active": True, "_id": {"$ne": candidate_id}},
            {"$set": {"active": False, "status": "inactive", "deactivatedAt": now}},
        )
        await self._collection.update_one(
            {"_id": candidate_id},
            {"$set": {"active": True, "status": "active", "activatedAt": now, "activatedBy": activated_by}},
        )
        return await self.find_by_id(model_id)

    async def deactivate(self, model_id: str) -> dict | None:
        if not ObjectId.is_valid(model_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(model_id), "active": False}, {"$set": {"status": "inactive"}}
        )
        return await self.find_by_id(model_id)
