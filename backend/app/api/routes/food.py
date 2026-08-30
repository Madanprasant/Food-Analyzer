from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_current_user, get_database
from app.repositories.food_analysis_repository import FoodAnalysisRepository
from app.repositories.nutrition_repository import NutritionRepository
from app.schemas.food import (
    AnalyzeFoodResponse,
    ConfirmFoodRequest,
    ConfirmFoodResponse,
    FoodHistoryItem,
    TopPredictionResponse,
)
from app.services.classifiers.efficientnet_v2_s import EfficientNetV2SClassifier
from app.services.image_storage import LocalImageStorage
from app.services.nutrition.calculator import calculate_serving
from app.services.nutrition.meal_balance import calculate_meal_balance

router = APIRouter(prefix="/food", tags=["food analysis"])
SUPPORTED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def serialize_history(document: dict) -> FoodHistoryItem:
    original = document["originalPrediction"]
    return FoodHistoryItem(
        analysis_id=str(document["_id"]),
        created_at=document["createdAt"],
        predicted_food=original["food"],
        confidence=original["confidence"],
        final_food=document.get("finalConfirmedFood"),
        was_corrected=document.get("wasCorrected"),
        status=document["status"],
    )


async def validate_and_read_image(upload: UploadFile, max_bytes: int) -> tuple[bytes, Image.Image]:
    if upload.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Upload a JPEG, PNG, or WebP image.")
    content = await upload.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=422, detail="The selected image is empty.")
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds the 5 MB upload limit.")
    try:
        image = Image.open(BytesIO(content))
        image.verify()
        image = Image.open(BytesIO(content)).convert("RGB")
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(status_code=422, detail="The uploaded file is not a valid image.") from error
    return content, image


@router.post("/analyze", response_model=AnalyzeFoodResponse)
async def analyze_food(
    request: Request,
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user),
    database: MongoDatabase = Depends(get_database),
) -> AnalyzeFoodResponse:
    settings = request.app.state.settings
    content, decoded_image = await validate_and_read_image(image, settings.max_upload_bytes)
    try:
        classifier = request.app.state.classifier_service.classifier
        result = await run_in_threadpool(classifier.predict, decoded_image)
        if not isinstance(classifier, EfficientNetV2SClassifier):
            raise RuntimeError("The configured classifier does not provide food-class metadata.")
        suffix = Path(image.filename or "upload.jpg").suffix
        image_reference = await run_in_threadpool(LocalImageStorage(settings.upload_dir).save, content, suffix)
        document = {
            "userId": user["_id"],
            "imageReference": image_reference,
            "createdAt": datetime.utcnow(),
            "originalPrediction": {"food": result.prediction.food, "confidence": result.prediction.confidence},
            "topK": [{"food": entry.food, "confidence": entry.confidence} for entry in result.top_k],
            "modelName": result.model_name,
            "modelVersion": result.model_version,
            "confidenceThreshold": settings.confidence_threshold,
            "lowConfidence": result.low_confidence,
            "status": "awaiting_confirmation",
        }
        saved = await FoodAnalysisRepository(database).create_prediction(document)
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return AnalyzeFoodResponse(
        analysis_id=str(saved["_id"]), predicted_food=result.prediction.food, confidence=result.prediction.confidence,
        top_k=[TopPredictionResponse(food=item.food, confidence=item.confidence) for item in result.top_k],
        low_confidence=result.low_confidence, confidence_threshold=settings.confidence_threshold,
        model_name=result.model_name, model_version=result.model_version,
    )


@router.post("/confirm", response_model=ConfirmFoodResponse)
async def confirm_food(
    payload: ConfirmFoodRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    database: MongoDatabase = Depends(get_database),
) -> ConfirmFoodResponse:
    classifier = request.app.state.classifier_service.classifier
    if not isinstance(classifier, EfficientNetV2SClassifier) or payload.final_food not in classifier.classes:
        raise HTTPException(status_code=422, detail="Choose a food from the available model classes.")
    try:
        existing = await FoodAnalysisRepository(database).find_for_user(payload.analysis_id, str(user["_id"]))
        if not existing:
            raise HTTPException(status_code=404, detail="Analysis was not found.")
        original_food = existing["originalPrediction"]["food"]
        nutrition_record = await NutritionRepository(database).get_by_model_class(payload.final_food)
        nutrition_snapshot = calculate_serving(nutrition_record, payload.serving_grams) if nutrition_record else None
        if nutrition_record and nutrition_record["status"] == "verified" and payload.serving_grams is None:
            nutrition_status = "serving_amount_required"
        else:
            nutrition_status = "verified" if nutrition_snapshot else "nutrition_pending"
        meal_balance = calculate_meal_balance(nutrition_snapshot, user.get("profile", {}))
        updated = await FoodAnalysisRepository(database).confirm(
            payload.analysis_id, str(user["_id"]), payload.final_food, payload.serving_multiplier,
            payload.final_food != original_food,
            payload.serving_grams, nutrition_snapshot, nutrition_status,
            nutrition_record.get("source") if nutrition_snapshot else None, meal_balance,
        )
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return ConfirmFoodResponse(
        analysis_id=str(updated["_id"]), final_food=payload.final_food,
        was_corrected=payload.final_food != original_food, serving_multiplier=payload.serving_multiplier,
        status=updated["status"], nutrition_status=updated["nutritionStatus"],
        nutrition_snapshot=updated.get("nutritionSnapshot"), meal_balance=updated["mealBalance"],
    )


@router.get("/history", response_model=list[FoodHistoryItem])
async def list_history(
    user: dict = Depends(get_current_user), database: MongoDatabase = Depends(get_database)
) -> list[FoodHistoryItem]:
    try:
        documents = await FoodAnalysisRepository(database).list_for_user(str(user["_id"]))
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return [serialize_history(document) for document in documents]
