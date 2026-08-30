from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.services.classifiers.base import FoodClassifier
from app.services.classifiers.efficientnet_v2_s import EfficientNetV2SClassifier


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
    ) -> EfficientNetV2SClassifier:
        if architecture != "efficientnet_v2_s":
            raise ValueError("Unsupported model architecture. The current upload registry supports efficientnet_v2_s only.")
        candidate = EfficientNetV2SClassifier(
            self._settings,
            model_path=Path(model_path),
            class_names_path=Path(class_names_path),
            model_name=model_name,
            model_version=model_version,
        )
        candidate.load_model()
        return candidate

    def activate_candidate(self, candidate: FoodClassifier) -> None:
        """Swap only an already validated, fully loaded model instance."""
        self._classifier = candidate
        self.startup_error = None
