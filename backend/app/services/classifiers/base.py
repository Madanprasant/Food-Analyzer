from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from PIL import Image


class ModelConfigurationError(RuntimeError):
    """Raised when a classifier cannot safely be initialized."""


@dataclass(frozen=True)
class FoodPrediction:
    food: str
    confidence: float
    index: int


@dataclass(frozen=True)
class PredictionResult:
    prediction: FoodPrediction
    top_k: list[FoodPrediction]
    model_name: str
    model_version: str
    low_confidence: bool


class FoodClassifier(ABC):
    """Stable contract for any current or future image classifier."""

    model_name: str
    model_version: str

    @abstractmethod
    def load_model(self) -> None:
        """Load and validate the model once during application startup."""

    @abstractmethod
    def predict(self, image: Image.Image) -> PredictionResult:
        """Return the highest confidence food prediction for an image."""

    @abstractmethod
    def predict_top_k(self, image: Image.Image, k: int = 5) -> list[FoodPrediction]:
        """Return the k most likely foods using actual model probabilities."""

    @abstractmethod
    def explain(self, image: Image.Image) -> Any:
        """Return a model-specific explanation, or a clear unsupported error."""
