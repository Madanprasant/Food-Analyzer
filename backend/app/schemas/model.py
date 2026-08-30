from pydantic import BaseModel, Field


class ModelStatusResponse(BaseModel):
    status: str
    model_name: str = "EfficientNetV2-S"
    model_version: str
    class_count: int | None = None
    confidence_threshold: float
    detail: str | None = None


class FoodClassResponse(BaseModel):
    classes: list[str]
    total: int = Field(ge=0)
