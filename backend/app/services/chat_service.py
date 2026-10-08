from __future__ import annotations

import re
from datetime import datetime, timezone

from app.services.gemini_service import GeminiService
from app.services.personalization.recommendations import build_recommendations
from app.services.rag_service import NutritionKnowledgeBase


_SCOPE_TERMS = {
    "food", "foods", "meal", "meals", "eat", "eaten", "ate", "consume", "consumed", "consumption",
    "calorie", "calories", "nutrition", "nutrient", "nutrients", "protein", "carbohydrate", "carbs",
    "fat", "fiber", "diet", "healthy", "healthier", "alternative", "recommendation", "plate", "history",
}
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_SCOPE_REPLY = "I can help only with your food history, meals, calories, nutrition, food alternatives, and meal recommendations."


def is_food_nutrition_question(message: str, knowledge_base: NutritionKnowledgeBase) -> bool:
    tokens = set(_TOKEN_PATTERN.findall(message.lower()))
    if tokens & _SCOPE_TERMS:
        return True
    return any(document.title.lower() in message.lower() for document in knowledge_base.retrieve(message, limit=4))


def _food_name(document: dict) -> str:
    return str(document.get("finalConfirmedFood") or document.get("originalPrediction", {}).get("food") or "Unknown food")


def _history_context(history: list[dict]) -> tuple[str, list[dict]]:
    if not history:
        return "No confirmed meals are available for this user yet.", []
    lines: list[str] = []
    sources: list[dict] = []
    for item in history:
        snapshot = item.get("nutritionSnapshot") or {}
        values = ", ".join(
            f"{label}: {snapshot[key]}" for key, label in (
                ("calories_kcal", "calories kcal"), ("protein_g", "protein g"),
                ("carbohydrate_g", "carbohydrate g"), ("fat_g", "fat g"), ("fiber_g", "fiber g"),
            ) if snapshot.get(key) is not None
        ) or "nutrition unavailable"
        created = item.get("createdAt")
        date_label = created.astimezone(timezone.utc).date().isoformat() if isinstance(created, datetime) and created.tzinfo else (created.date().isoformat() if isinstance(created, datetime) else "unknown date")
        food = _food_name(item)
        lines.append(f"- {date_label}: {food}; {values}.")
        sources.append({"type": "history", "title": f"Logged meal: {food} ({date_label})"})
    return "\n".join(lines), sources


class FoodNutritionChatService:
    def __init__(self, knowledge_base: NutritionKnowledgeBase, llm: GeminiService) -> None:
        self._knowledge_base = knowledge_base
        self._llm = llm

    async def answer(self, message: str, history: list[dict], profile: dict | None = None) -> tuple[str, list[dict], bool]:
        cleaned = message.strip()
        if not is_food_nutrition_question(cleaned, self._knowledge_base):
            return _SCOPE_REPLY, [], False
        documents = self._knowledge_base.retrieve(cleaned)
        history_text, history_sources = _history_context(history)
        knowledge_text = "\n".join(f"- {document.content}" for document in documents)
        sources = history_sources + [{"type": "nutrition_knowledge", "title": document.title} for document in documents]
        recommendation_text = "Not requested."
        if {"recommend", "recommendation", "next", "alternative", "healthier"} & set(_TOKEN_PATTERN.findall(cleaned.lower())):
            recommendations = build_recommendations(history, profile or {})
            recommendation_text = "\n".join(
                f"- {item['title']}: {item['food']}. Reason: {item['reason']}" for item in recommendations
            )
            sources.extend({"type": "recommendation", "title": item["title"]} for item in recommendations)
        system_instruction = (
            "You are PLATESIGNAL's food and nutrition assistant. Answer only questions about the user's food consumption, "
            "food history, meals, calories, nutrition, food alternatives, and practical meal recommendations. "
            "Use only the supplied user history and nutrition knowledge. Never claim facts absent from that context. "
            "Do not diagnose, treat, or prevent medical conditions; advise a qualified professional for medical concerns. "
            "Keep the answer concise and helpful."
        )
        prompt = f"User question: {cleaned}\n\nAuthenticated user's recent meal history:\n{history_text}\n\nRetrieved nutrition knowledge:\n{knowledge_text}\n\nPersonalized recommendation results:\n{recommendation_text}"
        return await self._llm.generate(system_instruction, prompt), sources, True
