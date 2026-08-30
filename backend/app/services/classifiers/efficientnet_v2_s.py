from __future__ import annotations

import json
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms
from torchvision.models import efficientnet_v2_s

from app.core.config import Settings
from app.services.classifiers.base import (
    FoodClassifier,
    FoodPrediction,
    ModelConfigurationError,
    PredictionResult,
)


class EfficientNetV2SClassifier(FoodClassifier):
    """EfficientNetV2-S adapter for the supplied 239-class state dictionary."""

    model_name = "EfficientNetV2-S"

    def __init__(
        self, settings: Settings, *, model_path: Path | None = None, class_names_path: Path | None = None,
        model_name: str | None = None, model_version: str | None = None,
    ) -> None:
        self.settings = settings
        self.model_path = model_path or settings.model_path
        self.class_names_path = class_names_path or settings.class_names_path
        self.model_name = model_name or settings.model_name
        self.model_version = model_version or settings.model_version
        self._model: torch.nn.Module | None = None
        self._classes: list[str] = []
        self._transform = transforms.Compose(
            [
                transforms.Resize((settings.model_image_size, settings.model_image_size)),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)
                ),
            ]
        )

    @property
    def classes(self) -> list[str]:
        if not self._classes:
            raise ModelConfigurationError("Food classifier has not been loaded.")
        return self._classes.copy()

    def load_model(self) -> None:
        self._validate_input_files()
        self._classes = self._load_class_names(self.class_names_path)
        state_dict = self._load_state_dict(self.model_path)

        output_features = state_dict.get("classifier.1.weight")
        if output_features is None or output_features.ndim != 2:
            raise ModelConfigurationError(
                "Checkpoint is not compatible with the expected EfficientNetV2-S classifier head."
            )
        checkpoint_classes = output_features.shape[0]
        if checkpoint_classes != len(self._classes):
            raise ModelConfigurationError(
                f"Model emits {checkpoint_classes} classes but class_names.json contains "
                f"{len(self._classes)} entries."
            )

        model = efficientnet_v2_s(weights=None)
        model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, checkpoint_classes)
        try:
            model.load_state_dict(state_dict, strict=True)
        except RuntimeError as error:
            raise ModelConfigurationError(
                "Checkpoint keys do not match torchvision's EfficientNetV2-S architecture."
            ) from error

        self._model = model.eval()

    def predict(self, image: Image.Image) -> PredictionResult:
        top_k = self.predict_top_k(image, k=5)
        primary = top_k[0]
        return PredictionResult(
            prediction=primary,
            top_k=top_k,
            model_name=self.model_name,
            model_version=self.model_version,
            low_confidence=primary.confidence < self.settings.confidence_threshold,
        )

    def predict_top_k(self, image: Image.Image, k: int = 5) -> list[FoodPrediction]:
        if self._model is None:
            raise ModelConfigurationError("Food classifier is unavailable. Check startup logs.")
        if not 1 <= k <= len(self._classes):
            raise ValueError(f"k must be between 1 and {len(self._classes)}.")

        normalized = image.convert("RGB")
        batch = self._transform(normalized).unsqueeze(0)
        with torch.inference_mode():
            probabilities = torch.softmax(self._model(batch)[0], dim=0)
            values, indices = torch.topk(probabilities, k=k)
        return [
            FoodPrediction(
                food=self._classes[index.item()],
                confidence=round(value.item(), 6),
                index=index.item(),
            )
            for value, index in zip(values, indices, strict=True)
        ]

    def explain(self, image: Image.Image) -> None:
        raise NotImplementedError(
            "Grad-CAM is not yet enabled. It will be exposed through a model-specific "
            "explanation service once the target layer has been verified."
        )

    def _validate_input_files(self) -> None:
        for label, path in (
            ("MODEL_PATH", self.model_path),
            ("CLASS_NAMES_PATH", self.class_names_path),
        ):
            if not path.is_file():
                raise ModelConfigurationError(f"{label} does not point to a readable file: {path}")

    @staticmethod
    def _load_class_names(path: Path) -> list[str]:
        try:
            contents = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ModelConfigurationError(f"Could not read class names file: {path}") from error
        if not isinstance(contents, list) or not contents or not all(
            isinstance(name, str) and name.strip() and len(name.strip()) <= 100 for name in contents
        ):
            raise ModelConfigurationError("Class names file must be a non-empty JSON array of strings.")
        normalized = [name.strip() for name in contents]
        if len(set(normalized)) != len(normalized):
            raise ModelConfigurationError("Class names file must not contain duplicate class names.")
        return normalized

    @staticmethod
    def _load_state_dict(path: Path) -> dict[str, torch.Tensor]:
        try:
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        except (OSError, RuntimeError, ValueError) as error:
            raise ModelConfigurationError(f"Could not load model checkpoint: {path}") from error
        if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            checkpoint = checkpoint["state_dict"]
        if not isinstance(checkpoint, dict) or not checkpoint:
            raise ModelConfigurationError("Checkpoint must contain a non-empty state dictionary.")
        return checkpoint
