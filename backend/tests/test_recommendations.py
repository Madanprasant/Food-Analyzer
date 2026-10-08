import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.recommendations import get_recommendations
from app.api.routes.recommendations import router
from app.db.mongodb import DatabaseUnavailableError
from app.dependencies.auth import get_current_user, get_database
from app.repositories.food_analysis_repository import FoodAnalysisRepository
from app.services.personalization.recommendations import build_recommendations

NOW = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
PROFILE = {"calorieTarget": 2000, "proteinTargetG": 80}


def meal(food: str, *, calories: float = 300, protein: float = 20, fiber: float = 6, score: int = 85, days_ago: int = 0) -> dict:
    return {"userId": "user-a", "status": "confirmed", "createdAt": NOW - timedelta(days=days_ago), "finalConfirmedFood": food, "nutritionSnapshot": {"calories_kcal": calories, "protein_g": protein, "fiber_g": fiber}, "mealBalance": {"score": score}}


def types_for(history: list[dict]) -> set[str]:
    return {item["type"] for item in build_recommendations(history, PROFILE, NOW)}


def test_calorie_based_recommendation() -> None:
    assert "lighter" in types_for([meal("rice", calories=1700, protein=60, fiber=18)])


def test_protein_based_recommendation() -> None:
    assert "protein" in types_for([meal("rice", calories=500, protein=20, fiber=18)])


def test_repeated_food_recommendation() -> None:
    recommendations = build_recommendations([meal("biryani", calories=550, days_ago=day) for day in range(3)], PROFILE, NOW)
    assert next(item for item in recommendations if item["type"] == "variety")["food"] == "Vegetable pulao with raita"


def test_low_balance_recommendation() -> None:
    assert "balance" in types_for([meal("rice", score=55)])


def test_user_history_isolation_is_preserved_by_user_scoped_input() -> None:
    own_history = [meal("idli", calories=300, protein=40, fiber=18)]
    assert "variety" not in types_for(own_history)
    assert all("Biryani" not in item["reason"] for item in build_recommendations(own_history, PROFILE, NOW))


def test_endpoint_queries_only_the_authenticated_users_history(monkeypatch) -> None:
    queried_user_ids: list[str] = []

    async def fake_history(self, user_id: str, start, end):
        queried_user_ids.append(user_id)
        return [meal("idli", calories=300, protein=40, fiber=18)]

    monkeypatch.setattr(FoodAnalysisRepository, "list_for_user_between", fake_history)
    database = SimpleNamespace(database=SimpleNamespace(foodAnalyses=object()))
    response = asyncio.run(get_recommendations({"_id": "authenticated-user", "profile": PROFILE}, database))
    assert queried_user_ids == ["authenticated-user"]
    assert response.recommendations


def test_recommendation_endpoint_requires_authentication() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(database=SimpleNamespace(foodAnalyses=object()))
    response = TestClient(app).get("/recommendations")
    assert response.status_code == 401


def test_authenticated_recommendation_endpoint_and_repository_error(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(database=SimpleNamespace(foodAnalyses=object()))
    app.dependency_overrides[get_current_user] = lambda: {"_id": "authenticated-user", "profile": PROFILE}

    async def fake_history(self, user_id: str, start, end):
        assert user_id == "authenticated-user"
        return [meal("idli", protein=40, fiber=18)]

    monkeypatch.setattr(FoodAnalysisRepository, "list_for_user_between", fake_history)
    response = TestClient(app).get("/recommendations")
    assert response.status_code == 200
    assert response.json()["recommendations"]

    async def unavailable_history(self, user_id: str, start, end):
        raise DatabaseUnavailableError("Database is unavailable")

    monkeypatch.setattr(FoodAnalysisRepository, "list_for_user_between", unavailable_history)
    unavailable = TestClient(app).get("/recommendations")
    assert unavailable.status_code == 503


def test_empty_history_explains_how_to_start() -> None:
    assert build_recommendations([], PROFILE, NOW)[0]["type"] == "start_tracking"
