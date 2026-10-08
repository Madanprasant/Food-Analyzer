from __future__ import annotations

import hashlib
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.repositories.model_repository import ModelRepository
from app.services.classifier_service import ClassifierService


class ModelValidationError(ValueError):
    pass


class ModelManagementService:
    """Versioned model lifecycle. Upload validates but never auto-activates."""

    def __init__(self, settings: Settings, repository: ModelRepository, classifier_service: ClassifierService) -> None:
        self.settings = settings
        self.repository = repository
        self.classifier_service = classifier_service
        self._activation_lock = asyncio.Lock()

    async def ensure_baseline(self) -> None:
        await self.repository.ensure_baseline({
            "modelName": self.settings.model_name,
            "version": self.settings.model_version,
            "architecture": "efficientnet_v2_s",
            "classCount": len(self.classifier_service.classifier.classes),
            "modelFilePath": str(self.settings.model_path),
            "classNamesFilePath": str(self.settings.class_names_path),
            "uploadedBy": None,
            "uploadedAt": datetime.now(timezone.utc),
            "active": True,
            "status": "active",
            "isBaseline": True,
            "checksum": self._checksum(self.settings.model_path),
        })

    async def store_validated_upload(
        self, *, model_bytes: bytes, class_bytes: bytes, model_name: str, version: str, architecture: str, uploaded_by: object
    ) -> dict:
        if not model_name.strip() or not version.strip():
            raise ModelValidationError("Model name and version are required.")
        if len(model_name.strip()) > 120 or len(version.strip()) > 120:
            raise ModelValidationError("Model name and version must be 120 characters or fewer.")
        if not model_bytes or not class_bytes:
            raise ModelValidationError("Both a model file and class_names.json are required.")
        if architecture not in {"auto", "efficientnet_v2_s", "convnextv2_v2_base"}:
            raise ModelValidationError("Unsupported architecture selection.")
        upload_id = uuid4().hex
        target = self.settings.model_upload_dir / upload_id
        target.mkdir(parents=True, exist_ok=False)
        model_path = target / "model.pth"
        classes_path = target / "class_names.json"
        try:
            model_path.write_bytes(model_bytes)
            classes_path.write_bytes(class_bytes)
            candidate = self.classifier_service.validate_candidate(
                model_path=str(model_path), class_names_path=str(classes_path), model_name=model_name.strip(),
                model_version=version.strip(), architecture=architecture,
            )
        except Exception as error:
            for path in (model_path, classes_path):
                if path.is_file():
                    path.unlink()
            if target.exists():
                target.rmdir()
            raise ModelValidationError(str(error)) from error
        document = {
            "modelName": model_name.strip(),
            "version": version.strip(),
            "architecture": getattr(candidate, "architecture", "efficientnet_v2_s"),
            "classCount": len(candidate.classes),
            "modelFilePath": str(model_path),
            "classNamesFilePath": str(classes_path),
            "uploadedBy": uploaded_by,
            "uploadedAt": datetime.now(timezone.utc),
            "active": False,
            "status": "validated",
            "isBaseline": False,
            "checksum": hashlib.sha256(model_bytes).hexdigest(),
        }
        return await self.repository.create(document)

    async def activate(self, model_id: str, activated_by: object) -> dict:
        async with self._activation_lock:
            metadata = await self.repository.find_by_id(model_id)
            if not metadata:
                raise ModelValidationError("Model version was not found.")
            if metadata.get("status") == "invalid":
                raise ModelValidationError("This invalid model version cannot be activated.")
            try:
                candidate = self.classifier_service.validate_candidate(
                    model_path=metadata["modelFilePath"], class_names_path=metadata["classNamesFilePath"],
                    model_name=metadata["modelName"], model_version=metadata["version"], architecture=metadata["architecture"],
                )
            except Exception as error:
                raise ModelValidationError(f"Model cannot be activated because validation failed: {error}") from error
            # Only a fully loaded candidate can reach this switch; the existing instance remains
            # available until the final in-memory assignment.
            updated = await self.repository.set_active(model_id, activated_by, datetime.now(timezone.utc))
            self.classifier_service.activate_candidate(candidate)
            return updated

    async def load_active_model(self) -> None:
        """Restore the selected active version at startup without replacing a usable baseline on failure."""
        active = await self.repository.find_active()
        if not active or active.get("isBaseline"):
            return
        try:
            candidate = self.classifier_service.validate_candidate(
                model_path=active["modelFilePath"], class_names_path=active["classNamesFilePath"],
                model_name=active["modelName"], model_version=active["version"], architecture=active["architecture"],
            )
        except Exception:
            return
        self.classifier_service.activate_candidate(candidate)

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
