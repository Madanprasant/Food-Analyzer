from __future__ import annotations

from datetime import datetime

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.db.mongodb import MongoDatabase


class DuplicateEmailError(ValueError):
    pass


class UserRepository:
    def __init__(self, database: MongoDatabase) -> None:
        self._collection = database.database.users

    async def create(self, email: str, password_hash: str, display_name: str) -> dict:
        now = datetime.utcnow()
        document = {
            "email": email.lower(),
            "passwordHash": password_hash,
            "profile": {"displayName": display_name},
            "isOnboarded": False,
            "createdAt": now,
            "updatedAt": now,
        }
        try:
            result = await self._collection.insert_one(document)
        except DuplicateKeyError as error:
            raise DuplicateEmailError("An account with this email already exists.") from error
        document["_id"] = result.inserted_id
        return document

    async def find_by_email(self, email: str) -> dict | None:
        return await self._collection.find_one({"email": email.lower()})

    async def find_by_firebase_uid(self, firebase_uid: str) -> dict | None:
        return await self._collection.find_one({"firebaseUid": firebase_uid})

    async def create_firebase_user(self, email: str, firebase_uid: str, display_name: str) -> dict:
        now = datetime.utcnow()
        document = {
            "email": email.lower(),
            "firebaseUid": firebase_uid,
            "authProvider": "firebase-google",
            "profile": {"displayName": display_name},
            "isOnboarded": False,
            "createdAt": now,
            "updatedAt": now,
        }
        try:
            result = await self._collection.insert_one(document)
        except DuplicateKeyError as error:
            raise DuplicateEmailError("An account with this email already exists. Sign in with its original method.") from error
        document["_id"] = result.inserted_id
        return document

    async def find_by_id(self, user_id: str) -> dict | None:
        if not ObjectId.is_valid(user_id):
            return None
        return await self._collection.find_one({"_id": ObjectId(user_id)})

    async def update_profile(self, user_id: str, changes: dict) -> dict | None:
        if not ObjectId.is_valid(user_id):
            return None
        payload = {f"profile.{key}": value for key, value in changes.items()}
        payload["updatedAt"] = datetime.utcnow()
        await self._collection.update_one({"_id": ObjectId(user_id)}, {"$set": payload})
        return await self.find_by_id(user_id)

    async def complete_onboarding(self, user_id: str, profile: dict) -> dict | None:
        if not ObjectId.is_valid(user_id):
            return None
        await self._collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"profile": profile, "isOnboarded": True, "updatedAt": datetime.utcnow()}},
        )
        return await self.find_by_id(user_id)
