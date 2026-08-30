from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.mongodb import MongoDatabase
from app.services.classifier_service import ClassifierService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    service = ClassifierService(settings)
    service.startup()
    app.state.settings = settings
    app.state.classifier_service = service
    database = MongoDatabase(settings)
    await database.startup()
    app.state.database = database
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
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
