from datetime import datetime

from pydantic import BaseModel, Field


class AdminStatusResponse(BaseModel):
    email: str
    role: str = "admin"


class ModelVersionResponse(BaseModel):
    id: str
    model_name: str
    version: str
    architecture: str
    class_count: int = Field(ge=1)
    uploaded_at: datetime
    uploaded_by: str | None = None
    active: bool
    status: str
    is_baseline: bool = False
    activated_at: datetime | None = None


class ModelVersionsResponse(BaseModel):
    models: list[ModelVersionResponse]
