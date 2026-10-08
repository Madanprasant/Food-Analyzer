from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.mongodb import MongoDatabase
from app.services.classifier_service import ClassifierService
from app.services.model_management import ModelManagementService
from app.repositories.model_repository import ModelRepository
from app.repositories.user_repository import UserRepository
from app.services.chat_service import FoodNutritionChatService
from app.services.gemini_service import GeminiService
from app.services.rag_service import NutritionKnowledgeBase


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    service = ClassifierService(settings)
    service.startup()

    app.state.settings = settings
    app.state.classifier_service = service

    # The shared knowledge base contains only public nutrition seed data
    # and is built once.
    app.state.chat_service = FoodNutritionChatService(
        NutritionKnowledgeBase.from_seed(settings.nutrition_seed_path),
        GeminiService(settings)
    )

    # MongoDB connection
    database = MongoDatabase(settings)
    await database.startup()

    # Display MongoDB connection status in terminal
    if database.available:
        print("✅ Connected to MongoDB Atlas")
    else:
        print("❌ Failed to connect to MongoDB Atlas")

    app.state.database = database

    app.state.model_management_service = None

    if database.available and not service.startup_error:
        await UserRepository(database).grant_admin_roles(
            settings.admin_emails
        )

        model_management = ModelManagementService(
            settings,
            ModelRepository(database),
            service
        )

        await model_management.ensure_baseline()
        await model_management.load_active_model()

        app.state.model_management_service = model_management

    yield

    await database.shutdown()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="API for Indian food recognition and nutrition personalization.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(
        api_router,
        prefix=settings.api_prefix
    )

    return app


app = create_app()