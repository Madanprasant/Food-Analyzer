import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes.chat import router
from app.core.config import Settings
from app.dependencies.auth import get_current_user, get_database
from app.repositories.food_analysis_repository import FoodAnalysisRepository
from app.services.chat_service import FoodNutritionChatService, is_food_nutrition_question
from app.services.gemini_service import GeminiService, LLMConfigurationError
from app.services.rag_service import NutritionKnowledgeBase


class FakeLLM:
    async def generate(self, system_instruction: str, prompt: str) -> str:
        assert "Authenticated user's recent meal history" in prompt
        assert "Retrieved nutrition knowledge" in prompt
        return "Your logged meal contains sourced nutrition information."


class RecordingLLM:
    def __init__(self) -> None:
        self.prompt = ""

    async def generate(self, system_instruction: str, prompt: str) -> str:
        self.prompt = prompt
        return "A practical next meal is available in your recommendations."


def knowledge_base() -> NutritionKnowledgeBase:
    return NutritionKnowledgeBase.from_seed(Settings().nutrition_seed_path)


def meal() -> dict:
    return {
        "status": "confirmed", "createdAt": datetime(2026, 10, 5, tzinfo=timezone.utc),
        "finalConfirmedFood": "apple", "nutritionSnapshot": {"calories_kcal": 62.38, "protein_g": 0.2},
    }


def test_nutrition_question_is_accepted_and_unrelated_question_is_rejected() -> None:
    base = knowledge_base()
    assert is_food_nutrition_question("How many calories did I eat today?", base)
    assert not is_food_nutrition_question("Write a poem about the moon", base)


def test_rag_retrieves_matching_food_knowledge() -> None:
    documents = knowledge_base().retrieve("What is the nutrition of apple?")
    assert documents[0].title == "apple"
    assert "calories" in documents[0].content


def test_missing_gemini_configuration_is_a_clean_error() -> None:
    service = GeminiService(Settings(gemini_api_key=None))
    try:
        asyncio.run(service.generate("system", "question"))
    except LLMConfigurationError as error:
        assert "GEMINI_API_KEY" in str(error)
    else:
        raise AssertionError("Expected Gemini configuration error")


def test_chat_service_rejects_out_of_scope_without_calling_llm() -> None:
    service = FoodNutritionChatService(knowledge_base(), FakeLLM())
    answer, sources, in_scope = asyncio.run(service.answer("What is the capital of France?", [meal()]))
    assert not in_scope
    assert not sources
    assert "only" in answer.lower()


def test_chat_uses_recommendation_engine_for_next_meal_question() -> None:
    llm = RecordingLLM()
    service = FoodNutritionChatService(knowledge_base(), llm)
    answer, sources, in_scope = asyncio.run(service.answer("What should I eat next?", [meal()], {"proteinTargetG": 80}))
    assert in_scope
    assert answer
    assert "Personalized recommendation results:" in llm.prompt
    assert any(source["type"] == "recommendation" for source in sources)


def test_authenticated_chat_uses_only_authenticated_user_history(monkeypatch) -> None:
    queried_user_ids: list[str] = []

    async def fake_history(self, user_id: str, limit: int = 12):
        queried_user_ids.append(user_id)
        return [meal()]

    monkeypatch.setattr(FoodAnalysisRepository, "list_recent_confirmed_for_user", fake_history)
    app = FastAPI()
    app.include_router(router)
    app.state.chat_service = FoodNutritionChatService(knowledge_base(), FakeLLM())
    database = SimpleNamespace(database=SimpleNamespace(foodAnalyses=object()))
    app.dependency_overrides[get_database] = lambda: database
    app.dependency_overrides[get_current_user] = lambda: {"_id": "authenticated-user", "profile": {}}
    response = TestClient(app).post("/chat", json={"message": "What did I eat today?"})
    assert response.status_code == 200
    assert response.json()["in_scope"] is True
    assert queried_user_ids == ["authenticated-user"]


def test_chat_denies_unauthenticated_requests() -> None:
    app = FastAPI()
    app.include_router(router)
    app.state.chat_service = FoodNutritionChatService(knowledge_base(), FakeLLM())
    app.dependency_overrides[get_database] = lambda: SimpleNamespace(database=SimpleNamespace(foodAnalyses=object()))
    response = TestClient(app).post("/chat", json={"message": "What did I eat today?"})
    assert response.status_code == 401
