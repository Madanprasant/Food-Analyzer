from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.core.config import Settings


class DatabaseUnavailableError(RuntimeError):
    """Raised instead of fabricating persistence when Atlas is not configured."""


class MongoDatabase:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncIOMotorClient | None = None
        self._database: AsyncIOMotorDatabase | None = None
        self.startup_error: str | None = None

    @property
    def available(self) -> bool:
        return self._database is not None and self.startup_error is None

    @property
    def database(self) -> AsyncIOMotorDatabase:
        if self._database is None:
            detail = self.startup_error or "MONGODB_URI is not configured."
            raise DatabaseUnavailableError(f"Database is unavailable: {detail}")
        return self._database

    async def startup(self) -> None:
        if not self._settings.mongodb_uri:
            self.startup_error = "MONGODB_URI is not configured."
            return
        try:
            self._client = AsyncIOMotorClient(self._settings.mongodb_uri, serverSelectionTimeoutMS=5000)
            await self._client.admin.command("ping")
            self._database = self._client[self._settings.database_name]
            await self._ensure_indexes()
        except Exception as error:
            self.startup_error = f"Could not connect to MongoDB Atlas: {error}"
            if self._client:
                self._client.close()
            self._client = None
            self._database = None

    async def shutdown(self) -> None:
        if self._client:
            self._client.close()
        self._client = None
        self._database = None

    async def _ensure_indexes(self) -> None:
        await self.database.users.create_index("email", unique=True, name="users_email_unique")
        await self.database.users.create_index("firebaseUid", unique=True, sparse=True, name="users_firebase_uid_unique")
        await self.database.nutritionFoods.create_index("modelClass", unique=True, name="nutrition_model_class_unique")
        await self.database.nutritionFoods.create_index("canonicalFood", name="nutrition_canonical_food")
        await self.database.foodAnalyses.create_index(
            [("userId", ASCENDING), ("createdAt", DESCENDING)], name="analysis_user_created_at"
        )
        await self.database.foodAnalyses.create_index("createdAt", name="analysis_created_at")
        await self.database.revokedTokens.create_index("expiresAt", expireAfterSeconds=0, name="token_expiry")
        await self.database.revokedTokens.create_index("jti", unique=True, name="token_jti_unique")
        await self.database.modelVersions.create_index(
            [("modelName", ASCENDING), ("version", ASCENDING)], unique=True, name="model_name_version_unique"
        )
        await self.database.modelVersions.create_index(
            "active", unique=True, partialFilterExpression={"active": True}, name="single_active_model"
        )
        await self.database.modelVersions.create_index("uploadedAt", name="model_uploaded_at")

    @staticmethod
    def now() -> datetime:
        return datetime.now(timezone.utc)
