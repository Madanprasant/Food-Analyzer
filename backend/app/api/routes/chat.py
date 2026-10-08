from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.db.mongodb import DatabaseUnavailableError, MongoDatabase
from app.dependencies.auth import get_current_user, get_database
from app.repositories.food_analysis_repository import FoodAnalysisRepository
from app.schemas.chat import ChatRequest, ChatResponse, ChatSource
from app.services.gemini_service import LLMConfigurationError, LLMServiceError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    request: Request,
    user: dict = Depends(get_current_user),
    database: MongoDatabase = Depends(get_database),
) -> ChatResponse:
    try:
        history = await FoodAnalysisRepository(database).list_recent_confirmed_for_user(str(user["_id"]), limit=12)
        answer, sources, in_scope = await request.app.state.chat_service.answer(
            payload.message, history, user.get("profile", {})
        )
    except DatabaseUnavailableError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except LLMServiceError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
    return ChatResponse(answer=answer, sources=[ChatSource.model_validate(item) for item in sources], in_scope=in_scope)
