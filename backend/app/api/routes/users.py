from fastapi import APIRouter, Depends, HTTPException, status

from app.api.routes.auth import serialize_user
from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_current_user, get_database
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserResponse
from app.schemas.user import OnboardingRequest, ProfileUpdateRequest
from app.services.personalization.target_calculator import suggest_starting_targets

router = APIRouter(prefix="/users", tags=["users"])


def to_storage_profile(profile: dict) -> dict:
    field_names = {
        "display_name": "displayName", "date_of_birth": "dateOfBirth", "height_cm": "heightCm",
        "weight_kg": "weightKg", "activity_level": "activityLevel", "fitness_goal": "fitnessGoal",
        "diet_preference": "dietPreference", "disliked_foods": "dislikedFoods",
        "preferred_foods": "preferredFoods", "calorie_target": "calorieTarget",
        "protein_target_g": "proteinTargetG", "nutrition_goals": "nutritionGoals",
        "sex_for_estimation": "sexForEstimation", "target_source": "targetSource",
    }
    return {field_names.get(key, key): value for key, value in profile.items()}


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)) -> UserResponse:
    return serialize_user(user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    payload: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
    database: MongoDatabase = Depends(get_database),
) -> UserResponse:
    changes = to_storage_profile(payload.model_dump(exclude_none=True))
    if not changes:
        return serialize_user(user)
    try:
        updated = await UserRepository(database).update_profile(str(user["_id"]), changes)
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return serialize_user(updated)


@router.post("/me/onboarding", response_model=UserResponse)
async def complete_onboarding(
    payload: OnboardingRequest,
    user: dict = Depends(get_current_user),
    database: MongoDatabase = Depends(get_database),
) -> UserResponse:
    try:
        profile = payload.model_dump()
        if payload.target_source == "suggested":
            suggested = suggest_starting_targets(
                age=payload.age, height_cm=payload.height_cm, weight_kg=payload.weight_kg,
                activity_level=payload.activity_level, fitness_goal=payload.fitness_goal,
                sex_for_estimation=payload.sex_for_estimation,
            )
            profile["calorie_target"] = suggested.calories
            profile["protein_target_g"] = suggested.protein_grams
        updated = await UserRepository(database).complete_onboarding(
            str(user["_id"]), to_storage_profile(profile)
        )
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return serialize_user(updated)
