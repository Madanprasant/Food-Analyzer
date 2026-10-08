from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.schemas.model import FoodClassResponse, ModelStatusResponse
from app.services.classifiers.base import FoodClassifier

router = APIRouter(tags=["system"])


@router.get("/health", response_model=ModelStatusResponse)
async def health(request: Request) -> ModelStatusResponse | JSONResponse:
    service = request.app.state.classifier_service
    settings = request.app.state.settings
    if service.startup_error:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ModelStatusResponse(
                status="degraded",
                model_version=settings.model_version,
                confidence_threshold=settings.confidence_threshold,
                detail=service.startup_error,
            ).model_dump(),
        )
    classifier = service.classifier
    class_count = len(classifier.classes) if isinstance(classifier, FoodClassifier) else None
    return ModelStatusResponse(
        status="ready",
        model_version=settings.model_version,
        class_count=class_count,
        confidence_threshold=settings.confidence_threshold,
    )


@router.get("/food/classes", response_model=FoodClassResponse)
async def list_food_classes(request: Request) -> FoodClassResponse:
    classifier = request.app.state.classifier_service.classifier
    if not isinstance(classifier, FoodClassifier):
        return FoodClassResponse(classes=[], total=0)
    classes = classifier.classes
    return FoodClassResponse(classes=classes, total=len(classes))
