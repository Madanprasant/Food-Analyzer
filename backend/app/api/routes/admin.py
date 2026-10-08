from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_database, require_admin
from app.repositories.model_repository import ModelRepository
from app.schemas.admin import AdminStatusResponse, ModelVersionResponse, ModelVersionsResponse
from app.services.model_management import ModelManagementService, ModelValidationError


router = APIRouter(prefix="/admin", tags=["admin model management"])
_MODEL_SUFFIXES = {".pt", ".pth"}


def _serialize(document: dict) -> ModelVersionResponse:
    return ModelVersionResponse(
        id=str(document["_id"]), model_name=document["modelName"], version=document["version"],
        architecture=document["architecture"], class_count=document["classCount"],
        uploaded_at=document["uploadedAt"], uploaded_by=str(document["uploadedBy"]) if document.get("uploadedBy") else None,
        active=bool(document.get("active")), status=document["status"], is_baseline=bool(document.get("isBaseline")),
        activated_at=document.get("activatedAt"),
    )


def _service(request: Request) -> ModelManagementService:
    service = getattr(request.app.state, "model_management_service", None)
    if not service:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model management is unavailable until the database and baseline model are ready.")
    return service


async def _read_upload(upload: UploadFile, maximum: int, label: str) -> bytes:
    content = await upload.read(maximum + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{label} is empty.")
    if len(content) > maximum:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"{label} exceeds the configured upload limit.")
    return content


@router.get("/me", response_model=AdminStatusResponse)
async def admin_me(admin: dict = Depends(require_admin)) -> AdminStatusResponse:
    return AdminStatusResponse(email=admin["email"])


@router.get("/models/active", response_model=ModelVersionResponse)
async def active_model(
    admin: dict = Depends(require_admin), database: MongoDatabase = Depends(get_database)
) -> ModelVersionResponse:
    try:
        model = await ModelRepository(database).find_active()
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    if not model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active model is registered.")
    return _serialize(model)


@router.get("/models", response_model=ModelVersionsResponse)
async def model_versions(
    admin: dict = Depends(require_admin), database: MongoDatabase = Depends(get_database)
) -> ModelVersionsResponse:
    try:
        models = await ModelRepository(database).list_all()
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return ModelVersionsResponse(models=[_serialize(item) for item in models])


@router.post("/models", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
async def upload_model(
    request: Request,
    model: UploadFile = File(...),
    class_names: UploadFile = File(...),
    model_name: str = Form(..., min_length=1, max_length=120),
    version: str = Form(..., min_length=1, max_length=120),
    architecture: str = Form("auto"),
    admin: dict = Depends(require_admin),
) -> ModelVersionResponse:
    if not model.filename or model.filename.rsplit(".", 1)[-1].lower() not in {"pt", "pth"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload a PyTorch .pt or .pth model file.")
    if not class_names.filename or not class_names.filename.lower().endswith(".json"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Upload class_names.json as a JSON file.")
    service = _service(request)
    try:
        model_bytes = await _read_upload(model, request.app.state.settings.max_model_upload_bytes, "Model file")
        class_bytes = await _read_upload(class_names, 2 * 1024 * 1024, "Class names file")
        saved = await service.store_validated_upload(
            model_bytes=model_bytes, class_bytes=class_bytes, model_name=model_name, version=version,
            architecture=architecture, uploaded_by=admin["_id"],
        )
    except ModelValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _serialize(saved)


@router.post("/models/{model_id}/activate", response_model=ModelVersionResponse)
async def activate_model(model_id: str, request: Request, admin: dict = Depends(require_admin)) -> ModelVersionResponse:
    try:
        model = await _service(request).activate(model_id, admin["_id"])
    except ModelValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _serialize(model)


@router.post("/models/{model_id}/rollback", response_model=ModelVersionResponse)
async def rollback_model(model_id: str, request: Request, admin: dict = Depends(require_admin)) -> ModelVersionResponse:
    """Rollback is a validated activation of a prior stored model version."""
    try:
        model = await _service(request).activate(model_id, admin["_id"])
    except ModelValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return _serialize(model)
