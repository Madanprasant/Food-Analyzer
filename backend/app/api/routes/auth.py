from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.security import create_access_token, hash_password, verify_password
from app.services.firebase_auth import FirebaseAuthService, FirebaseConfigurationError
from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_current_user, get_database
from app.repositories.user_repository import DuplicateEmailError, UserRepository
from app.schemas.auth import AuthResponse, FirebaseTokenRequest, LoginRequest, UserResponse, SignupRequest

router = APIRouter(prefix="/auth", tags=["authentication"])


def serialize_user(user: dict) -> UserResponse:
    profile = user.get("profile", {})
    return UserResponse(
        id=str(user["_id"]),
        email=user["email"],
        profile={
            "display_name": profile.get("displayName", ""),
            "date_of_birth": profile.get("dateOfBirth"),
            "age": profile.get("age"),
            "height_cm": profile.get("heightCm"),
            "weight_kg": profile.get("weightKg"),
            "activity_level": profile.get("activityLevel"),
            "fitness_goal": profile.get("fitnessGoal"),
            "diet_preference": profile.get("dietPreference"),
            "allergies": profile.get("allergies", []),
            "disliked_foods": profile.get("dislikedFoods", []),
            "preferred_foods": profile.get("preferredFoods", []),
            "calorie_target": profile.get("calorieTarget"),
            "protein_target_g": profile.get("proteinTargetG"),
            "nutrition_goals": profile.get("nutritionGoals", []),
            "sex_for_estimation": profile.get("sexForEstimation"),
            "target_source": profile.get("targetSource"),
        },
        is_onboarded=user.get("isOnboarded", False),
        created_at=user["createdAt"],
    )


async def issue_auth_response(user: dict, request: Request) -> AuthResponse:
    token, expires_at, _ = create_access_token(str(user["_id"]), request.app.state.settings)
    return AuthResponse(access_token=token, expires_at=expires_at, user=serialize_user(user))


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest, request: Request, database: MongoDatabase = Depends(get_database)
) -> AuthResponse:
    try:
        user = await UserRepository(database).create(
            email=str(payload.email), password_hash=hash_password(payload.password), display_name=payload.display_name
        )
    except DuplicateEmailError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return await issue_auth_response(user, request)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest, request: Request, database: MongoDatabase = Depends(get_database)
) -> AuthResponse:
    try:
        user = await UserRepository(database).find_by_email(str(payload.email))
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    if not user or not verify_password(payload.password, user["passwordHash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")
    return await issue_auth_response(user, request)


@router.post("/firebase", response_model=AuthResponse)
async def firebase_sign_in(
    payload: FirebaseTokenRequest, request: Request, database: MongoDatabase = Depends(get_database)
) -> AuthResponse:
    try:
        claims = FirebaseAuthService(request.app.state.settings).verify_google_id_token(payload.id_token)
        repository = UserRepository(database)
        user = await repository.find_by_firebase_uid(claims["uid"])
        if not user:
            user = await repository.create_firebase_user(
                email=claims["email"], firebase_uid=claims["uid"],
                display_name=claims.get("name") or claims["email"].split("@", 1)[0],
            )
    except FirebaseConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except DuplicateEmailError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return await issue_auth_response(user, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    user: dict = Depends(get_current_user),
) -> None:
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    from app.core.security import decode_access_token

    payload = decode_access_token(token, request.app.state.settings)
    expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    await request.app.state.database.database.revokedTokens.insert_one(
        {"jti": payload["jti"], "userId": str(user["_id"]), "expiresAt": expires_at}
    )


@router.get("/me", response_model=UserResponse)
async def current_user(user: dict = Depends(get_current_user)) -> UserResponse:
    return serialize_user(user)
