from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms
from transformers import ConvNextV2Config, ConvNextV2ForImageClassification

from app.core.config import Settings
from app.services.classifiers.base import FoodClassifier, FoodPrediction, ModelConfigurationError, PredictionResult
from app.services.classifiers.efficientnet_v2_s import EfficientNetV2SClassifier


class ConvNeXtV2BaseClassifier(FoodClassifier):
    """Hugging Face ConvNeXt V2 Base adapter for the training checkpoint layout."""

    architecture = "convnextv2_v2_base"
    _IMAGE_SIZE = 224
    _CLASS_COUNT = 239
    _HIDDEN_SIZE = 1024

    def __init__(self, settings: Settings, *, model_path: Path, class_names_path: Path, model_name: str, model_version: str) -> None:
        self.settings = settings
        self.model_path = model_path
        self.class_names_path = class_names_path
        self.model_name = model_name
        self.model_version = model_version
        self._model: ConvNextV2ForImageClassification | None = None
        self._classes: list[str] = []
        self._transform = transforms.Compose([
            transforms.Resize((self._IMAGE_SIZE, self._IMAGE_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ])

    @property
    def classes(self) -> list[str]:
        if not self._classes:
            raise ModelConfigurationError("Food classifier has not been loaded.")
        return self._classes.copy()

    @classmethod
    def is_matching_state_dict(cls, state_dict: Mapping[str, object]) -> bool:
        classifier_weight = state_dict.get("classifier.weight")
        return (
            any(key.startswith("convnextv2.embeddings.") for key in state_dict)
            and any(key.startswith("convnextv2.encoder.") for key in state_dict)
            and getattr(classifier_weight, "ndim", None) == 2
            and tuple(classifier_weight.shape) == (cls._CLASS_COUNT, cls._HIDDEN_SIZE)
            and getattr(state_dict.get("classifier.bias"), "shape", None) == (cls._CLASS_COUNT,)
        )

    def load_model(self) -> None:
        if not self.model_path.is_file() or not self.class_names_path.is_file():
            raise ModelConfigurationError("ConvNeXt V2 model and class names files must be readable.")
        self._classes = EfficientNetV2SClassifier._load_class_names(self.class_names_path)
        if len(self._classes) != self._CLASS_COUNT:
            raise ModelConfigurationError("ConvNeXt V2 Base requires exactly 239 class names.")
        state_dict = self._load_state_dict(self.model_path)
        if not self.is_matching_state_dict(state_dict):
            raise ModelConfigurationError("Checkpoint is not a supported ConvNeXt V2 Base state dict with a 1024 → 239 classifier.")
        config = ConvNextV2Config(
            image_size=self._IMAGE_SIZE,
            num_channels=3,
            patch_size=4,
            hidden_sizes=[128, 256, 512, 1024],
            depths=[3, 3, 27, 3],
            num_labels=self._CLASS_COUNT,
        )
        model = ConvNextV2ForImageClassification(config)
        try:
            model.load_state_dict(dict(state_dict), strict=True)
        except RuntimeError as error:
            raise ModelConfigurationError("Checkpoint keys do not strictly match ConvNextV2ForImageClassification Base.") from error
        model.eval()
        try:
            with torch.inference_mode():
                logits = model(pixel_values=torch.zeros(1, 3, self._IMAGE_SIZE, self._IMAGE_SIZE)).logits
            if tuple(logits.shape) != (1, self._CLASS_COUNT):
                raise ModelConfigurationError("ConvNeXt V2 Base dummy inference did not return 239 class scores.")
        except ModelConfigurationError:
            raise
        except Exception as error:
            raise ModelConfigurationError("ConvNeXt V2 Base dummy 224×224 RGB inference failed.") from error
        self._model = model

    def predict(self, image: Image.Image) -> PredictionResult:
        top_k = self.predict_top_k(image, k=5)
        primary = top_k[0]
        return PredictionResult(prediction=primary, top_k=top_k, model_name=self.model_name, model_version=self.model_version, low_confidence=primary.confidence < self.settings.confidence_threshold)

    def predict_top_k(self, image: Image.Image, k: int = 5) -> list[FoodPrediction]:
        if self._model is None:
            raise ModelConfigurationError("Food classifier is unavailable. Check startup logs.")
        if not 1 <= k <= len(self._classes):
            raise ValueError(f"k must be between 1 and {len(self._classes)}.")
        batch = self._transform(image.convert("RGB")).unsqueeze(0)
        with torch.inference_mode():
            logits = self._model(pixel_values=batch).logits[0]
            values, indices = torch.topk(torch.softmax(logits, dim=0), k=k)
        return [FoodPrediction(food=self._classes[index.item()], confidence=round(value.item(), 6), index=index.item()) for value, index in zip(values, indices, strict=True)]

    def explain(self, image: Image.Image) -> None:
        raise NotImplementedError("Grad-CAM is not enabled for ConvNeXt V2 Base.")

    @staticmethod
    def _load_state_dict(path: Path) -> Mapping[str, object]:
        try:
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        except (OSError, RuntimeError, ValueError) as error:
            raise ModelConfigurationError(f"Could not load model checkpoint: {path}") from error
        state_dict = checkpoint.get("model_state_dict", checkpoint) if isinstance(checkpoint, dict) else checkpoint
        if not isinstance(state_dict, Mapping) or not state_dict:
            raise ModelConfigurationError("ConvNeXt V2 checkpoint must be a non-empty PyTorch state dict.")
        return {str(key).removeprefix("module."): value for key, value in state_dict.items()}
