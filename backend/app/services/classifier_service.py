from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.classifiers.base import FoodClassifier
from app.services.classifiers.efficientnet_v2_s import EfficientNetV2SClassifier
from app.services.classifiers.convnext_v2_base import ConvNeXtV2BaseClassifier


class ClassifierService:
    """Owns the process-wide classifier instance; it is never loaded per request."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._classifier: FoodClassifier = EfficientNetV2SClassifier(settings)
        self.startup_error: str | None = None

    @property
    def classifier(self) -> FoodClassifier:
        if self.startup_error:
            raise RuntimeError(self.startup_error)
        return self._classifier

    def startup(self) -> None:
        try:
            self._classifier.load_model()
        except Exception as error:
            self.startup_error = str(error)

    def validate_candidate(
        self, *, model_path: str, class_names_path: str, model_name: str, model_version: str, architecture: str
    ) -> FoodClassifier:
        detected = self.detect_architecture(Path(model_path))
        if architecture not in {"auto", detected}:
            raise ValueError(f"Uploaded checkpoint is {detected}, not {architecture}.")
        if detected == "efficientnet_v2_s":
            candidate: FoodClassifier = EfficientNetV2SClassifier(self._settings, model_path=Path(model_path), class_names_path=Path(class_names_path), model_name=model_name, model_version=model_version)
        elif detected == "convnextv2_v2_base":
            candidate = ConvNeXtV2BaseClassifier(self._settings, model_path=Path(model_path), class_names_path=Path(class_names_path), model_name=model_name, model_version=model_version)
        else:
            raise ValueError("Unsupported model architecture.")
        candidate.load_model()
        return candidate

    @staticmethod
    def detect_architecture(model_path: Path) -> str:
        """Identify supported checkpoint layouts without trusting form-provided architecture."""
        import torch
        try:
            checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
        except (OSError, RuntimeError, ValueError) as error:
            raise ValueError(f"Could not load model checkpoint: {model_path}") from error
        state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        if isinstance(state_dict, dict):
            normalized = {str(key).removeprefix("module."): value for key, value in state_dict.items()}
            if ConvNeXtV2BaseClassifier.is_matching_state_dict(normalized):
                return "convnextv2_v2_base"
        state_dict = checkpoint.get("state_dict", checkpoint) if isinstance(checkpoint, dict) else None
        weight = state_dict.get("classifier.1.weight") if isinstance(state_dict, dict) else None
        if getattr(weight, "ndim", None) == 2:
            return "efficientnet_v2_s"
        raise ValueError("Unsupported checkpoint. Expected EfficientNetV2-S or ConvNeXt V2 Base state-dict weights.")

    def activate_candidate(self, candidate: FoodClassifier) -> None:
        """Swap only an already validated, fully loaded model instance."""
        self._classifier = candidate
        self.startup_error = None
