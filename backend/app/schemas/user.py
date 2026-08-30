from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.auth import ProfileResponse


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    date_of_birth: str | None = None
    age: int | None = Field(default=None, ge=13, le=120)
    height_cm: float | None = Field(default=None, ge=50, le=300)
    weight_kg: float | None = Field(default=None, ge=15, le=500)
    activity_level: str | None = None
    fitness_goal: str | None = None
    diet_preference: str | None = None
    allergies: list[str] | None = None
    disliked_foods: list[str] | None = None
    preferred_foods: list[str] | None = None
    calorie_target: int | None = Field(default=None, ge=800, le=10000)
    protein_target_g: int | None = Field(default=None, ge=0, le=500)
    nutrition_goals: list[str] | None = None
    sex_for_estimation: Literal["female", "male", "prefer_not_to_say"] | None = None
    target_source: Literal["suggested", "custom"] | None = None


class OnboardingRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    age: int = Field(ge=13, le=120)
    height_cm: float = Field(ge=50, le=300)
    weight_kg: float = Field(ge=15, le=500)
    activity_level: str = Field(min_length=1, max_length=50)
    fitness_goal: str = Field(min_length=1, max_length=80)
    diet_preference: str = Field(min_length=1, max_length=80)
    allergies: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    preferred_foods: list[str] = Field(default_factory=list)
    sex_for_estimation: Literal["female", "male", "prefer_not_to_say"] = "prefer_not_to_say"
    target_source: Literal["suggested", "custom"] = "suggested"
    calorie_target: int | None = Field(default=None, ge=800, le=10000)
    protein_target_g: int | None = Field(default=None, ge=0, le=500)
    nutrition_goals: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_custom_calorie_target(self) -> "OnboardingRequest":
        if self.target_source == "custom" and self.calorie_target is None:
            raise ValueError("Enter a daily calorie target or choose suggested targets.")
        return self


class UserProfileResponse(BaseModel):
    profile: ProfileResponse
    is_onboarded: bool
