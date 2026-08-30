# PlateSignal — Indian Food Nutrition System

PlateSignal is a full-stack final-year project for recognizing Indian food from an image, confirming the result, and evaluating a meal against an individual’s nutrition profile.

## Current implementation status

**Phase 1 complete:** project structure, dark visual design system, model abstraction, supplied checkpoint validation, and API health/class endpoints.

The supplied checkpoint is an EfficientNetV2-S state dictionary with a 239-output classifier head. It matches the supplied JSON file containing 239 food classes.

## Architecture

```text
frontend/       React + Vite client
backend/        FastAPI API, security, persistence, domain services
ml/             replaceable model assets and class names
docs/           architecture and operational documentation
```

`FoodClassifier` is the model contract. The included `EfficientNetV2SClassifier` is an adapter, so changing model implementations does not require frontend changes.

## Run locally

### Backend

1. Create and activate a Python virtual environment.
2. Install `backend/requirements.txt`.
3. Copy `.env.example` to `.env` and set `MONGODB_URI` and a strong `JWT_SECRET` before using authentication.
4. From `backend`, run `uvicorn app.main:app --reload`.
5. Visit `http://127.0.0.1:8000/docs`.

### Frontend

1. From `frontend`, run `npm install`.
2. Run `npm run dev`.
3. Visit the local address shown by Vite, normally `http://localhost:5173`.

## Model replacement

1. Place a new checkpoint in `ml/models` and matching class JSON in `ml`.
2. Update `MODEL_PATH`, `CLASS_NAMES_PATH`, and `MODEL_VERSION`.
3. Implement or select a compatible `FoodClassifier` adapter.
4. Restart the backend. It verifies files and output-class count before serving predictions.

## Planned integrations

- MongoDB Atlas persistence, authentication, onboarding, and profile
- image analysis, correction, nutrition repository, and recommendations
- Grad-CAM for the verified classifier architecture
- real history/dashboard views
- LLM/RAG provider adapters; no LLM responses will be fabricated
