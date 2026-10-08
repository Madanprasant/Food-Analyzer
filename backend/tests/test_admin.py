import asyncio
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.admin import router
from app.core.config import Settings
from app.dependencies.auth import get_current_user, get_database
from app.services.model_management import ModelManagementService, ModelValidationError
from app.services.classifier_service import ClassifierService


class FakeRepository:
    def __init__(self) -> None:
        self.models: dict[str, dict] = {}
        self.active_id = "baseline"
        self.models[self.active_id] = {
            "_id": self.active_id, "modelName": "Baseline", "version": "v1", "architecture": "efficientnet_v2_s",
            "classCount": 2, "modelFilePath": "baseline.pth", "classNamesFilePath": "baseline.json", "active": True,
            "status": "active", "isBaseline": True, "uploadedAt": datetime.now(timezone.utc),
        }

    async def create(self, document: dict) -> dict:
        identifier = f"candidate-{len(self.models)}"
        document["_id"] = identifier
        self.models[identifier] = document
        return document

    async def find_by_id(self, model_id: str) -> dict | None:
        return self.models.get(model_id)

    async def set_active(self, model_id: str, activated_by: object, now: datetime) -> dict:
        for model in self.models.values():
            model["active"] = False
            if model["status"] == "active": model["status"] = "inactive"
        model = self.models[model_id]
        model.update({"active": True, "status": "active", "activatedBy": activated_by, "activatedAt": now})
        self.active_id = model_id
        return model


class FakeClassifier:
    def __init__(self, *, reject_paths: set[str] | None = None) -> None:
        self.reject_paths = reject_paths or set()
        self.active = "baseline"

    def validate_candidate(self, *, model_path: str, **kwargs):
        if model_path == "baseline.pth":
            return SimpleNamespace(classes=["apple", "banana"], marker=model_path)
        if model_path in self.reject_paths or b"invalid" in Path(model_path).read_bytes():
            raise ValueError("Candidate checkpoint is invalid.")
        return SimpleNamespace(classes=["apple", "banana"], marker=model_path)

    def activate_candidate(self, candidate) -> None:
        self.active = candidate.marker


def management_service(tmp_path: Path, classifier: FakeClassifier | None = None):
    settings = Settings(model_upload_dir=tmp_path)
    repository = FakeRepository()
    service = ModelManagementService(settings, repository, classifier or FakeClassifier())
    return service, repository


def test_invalid_model_upload_is_rejected_and_does_not_create_a_version(tmp_path: Path) -> None:
    service, repository = management_service(tmp_path)
    try:
        asyncio.run(service.store_validated_upload(
            model_bytes=b"invalid checkpoint", class_bytes=b'["apple", "banana"]', model_name="Test", version="v2",
            architecture="efficientnet_v2_s", uploaded_by="admin",
        ))
    except ModelValidationError:
        pass
    else:
        raise AssertionError("Invalid model was accepted")
    assert len(repository.models) == 1


def test_valid_upload_is_stored_in_a_generated_directory(tmp_path: Path) -> None:
    service, repository = management_service(tmp_path)
    saved = asyncio.run(service.store_validated_upload(
        model_bytes=b"valid checkpoint", class_bytes=b'["apple", "banana"]', model_name="Test", version="v2",
        architecture="efficientnet_v2_s", uploaded_by="admin",
    ))
    assert saved["status"] == "validated"
    assert saved["active"] is False
    assert Path(saved["modelFilePath"]).parent.parent == tmp_path
    assert ".." not in Path(saved["modelFilePath"]).parts
    assert len(repository.models) == 2


def test_activation_and_rollback_keep_versions_available(tmp_path: Path) -> None:
    classifier = FakeClassifier()
    service, repository = management_service(tmp_path, classifier)
    candidate = asyncio.run(service.store_validated_upload(
        model_bytes=b"valid checkpoint", class_bytes=b'["apple", "banana"]', model_name="Test", version="v2",
        architecture="efficientnet_v2_s", uploaded_by="admin",
    ))
    activated = asyncio.run(service.activate(candidate["_id"], "admin"))
    assert activated["active"] is True
    assert classifier.active == candidate["modelFilePath"]
    assert repository.models["baseline"]["active"] is False
    rolled_back = asyncio.run(service.activate("baseline", "admin"))
    assert rolled_back["active"] is True
    assert repository.models[candidate["_id"]]["status"] == "inactive"


def test_failed_activation_leaves_current_classifier_and_metadata_active(tmp_path: Path) -> None:
    classifier = FakeClassifier(reject_paths={"bad.pth"})
    service, repository = management_service(tmp_path, classifier)
    repository.models["bad"] = {
        "_id": "bad", "modelName": "Bad", "version": "v2", "architecture": "efficientnet_v2_s", "classCount": 2,
        "modelFilePath": "bad.pth", "classNamesFilePath": "bad.json", "active": False, "status": "validated",
        "isBaseline": False, "uploadedAt": datetime.now(timezone.utc),
    }
    try:
        asyncio.run(service.activate("bad", "admin"))
    except ModelValidationError:
        pass
    else:
        raise AssertionError("Bad model was activated")
    assert repository.models["baseline"]["active"] is True
    assert classifier.active == "baseline"


def test_admin_route_denies_normal_user_and_allows_admin() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(database=SimpleNamespace())
    app.dependency_overrides[get_current_user] = lambda: {"_id": "person", "email": "person@example.com", "role": "user"}
    # Dependency nesting resolves the current user first; request state is needed by require_admin.
    app.state.settings = SimpleNamespace(admin_emails=[])
    client = TestClient(app)
    assert client.get("/admin/me").status_code == 403
    app.dependency_overrides[get_current_user] = lambda: {"_id": "admin", "email": "admin@example.com", "role": "admin"}
    assert client.get("/admin/me").status_code == 200


def test_detects_convnext_v2_deployment_checkpoint(tmp_path: Path) -> None:
    import torch
    from collections import OrderedDict

    checkpoint_path = tmp_path / "convnextv2_indian_food_239_deployment.pth"
    torch.save(OrderedDict({
        "convnextv2.embeddings.patch_embeddings.weight": torch.zeros(128, 3, 4, 4),
        "convnextv2.encoder.stages.0.layers.0.dwconv.weight": torch.zeros(128, 1, 7, 7),
        "classifier.weight": torch.zeros(239, 1024),
        "classifier.bias": torch.zeros(239),
    }), checkpoint_path)
    assert ClassifierService.detect_architecture(checkpoint_path) == "convnextv2_v2_base"


def test_detects_existing_efficientnet_checkpoint(tmp_path: Path) -> None:
    import torch

    checkpoint_path = tmp_path / "efficientnet.pth"
    torch.save({"classifier.1.weight": torch.zeros(239, 1280)}, checkpoint_path)
    assert ClassifierService.detect_architecture(checkpoint_path) == "efficientnet_v2_s"
