from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.services.nutrition.seed import load_normalized_seed


_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {"a", "an", "and", "are", "about", "can", "did", "do", "for", "i", "is", "me", "my", "of", "the", "to", "what", "with", "you", "your"}


def _tokens(text: str) -> Counter[str]:
    return Counter(token for token in _TOKEN_PATTERN.findall(text.lower()) if token not in _STOP_WORDS)


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    content: str
    vector: Counter[str]


class NutritionKnowledgeBase:
    """Small in-memory lexical retriever built once at application startup."""

    def __init__(self, documents: list[KnowledgeDocument]) -> None:
        self._documents = documents

    @classmethod
    def from_seed(cls, seed_path: Path) -> "NutritionKnowledgeBase":
        documents: list[KnowledgeDocument] = []
        for record in load_normalized_seed(seed_path):
            nutrients = record["nutrients"]
            facts = [
                f"Food: {record['canonicalFood']}.",
                f"Nutrition status: {record['status']}.",
            ]
            if record["status"] == "verified":
                available = [
                    f"{label} {nutrients[key]}" for key, label in (
                        ("calories_kcal", "calories kcal per 100 g,"), ("protein_g", "protein g,"),
                        ("carbohydrate_g", "carbohydrate g,"), ("fat_g", "fat g,"), ("fiber_g", "fiber g")
                    ) if nutrients.get(key) is not None
                ]
                facts.append(" ".join(available) + ".")
                facts.append("Source: ICMR-NIN IFCT 2017.")
            else:
                facts.append("Verified nutrition values are not available; do not estimate or invent them.")
            content = " ".join(facts)
            documents.append(KnowledgeDocument(record["canonicalFood"], content, _tokens(content)))
        guidance = "General guidance: nutrition figures in this application are only provided when sourced. Food variety, vegetables, legumes, and appropriate portions can support balanced meals. This application does not diagnose, treat, or replace a clinician or dietitian."
        documents.append(KnowledgeDocument("General nutrition guidance", guidance, _tokens(guidance)))
        return cls(documents)

    def retrieve(self, query: str, limit: int = 4) -> list[KnowledgeDocument]:
        query_vector = _tokens(query)
        scored: list[tuple[int, KnowledgeDocument]] = []
        for document in self._documents:
            score = sum(min(query_vector[token], count) for token, count in document.vector.items())
            if score:
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], item[1].title))
        if not scored:
            return [document for document in self._documents if document.title == "General nutrition guidance"]
        return [document for _, document in scored[:limit]]
