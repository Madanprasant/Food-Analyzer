from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    display_name: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class FirebaseTokenRequest(BaseModel):
    id_token: str = Field(min_length=1)


class ProfileResponse(BaseModel):
    display_name: str
    date_of_birth: str | None = None
    age: int | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    activity_level: str | None = None
    fitness_goal: str | None = None
    diet_preference: str | None = None
    allergies: list[str] = Field(default_factory=list)
    disliked_foods: list[str] = Field(default_factory=list)
    preferred_foods: list[str] = Field(default_factory=list)
    calorie_target: int | None = None
    protein_target_g: int | None = None
    nutrition_goals: list[str] = Field(default_factory=list)
    sex_for_estimation: str | None = None
    target_source: str | None = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    profile: ProfileResponse
    is_onboarded: bool
    created_at: datetime


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse
