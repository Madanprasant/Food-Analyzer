from fastapi import APIRouter

from app.api.routes import admin, auth, chat, food, nutrition, recommendations, system, users

api_router = APIRouter()
api_router.include_router(system.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(food.router)
api_router.include_router(nutrition.router)
api_router.include_router(recommendations.router)
api_router.include_router(chat.router)
api_router.include_router(admin.router)
