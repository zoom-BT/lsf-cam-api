"""
API FastAPI pour LSF-Cam
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    HealthResponse
)
from app.model_loader import predictor


# === Lifespan (chargement au démarrage) ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Charge le modèle au démarrage"""
    print("Chargement du modèle...")
    try:
        predictor.load()
        print("Modèle chargé avec succès")
    except Exception as e:
        print(f"Erreur chargement: {e}")
    yield
    print("Arrêt de l'API")


# === Application ===

app = FastAPI(
    title="LSF-Cam API",
    description="API de reconnaissance de la Langue des Signes Camerounaise",
    version="1.0.0",
    lifespan=lifespan
)

# CORS (pour accès depuis une app web/mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Endpoints ===

@app.get("/", tags=["Info"])
async def root():
    """Page d'accueil"""
    return {
        "message": "LSF-Cam API",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse, tags=["Info"])
async def health():
    """Vérifie l'état de l'API"""
    return HealthResponse(
        status="ok",
        model_loaded=predictor.model is not None,
        version="1.0.0"
    )


@app.get("/classes", tags=["Info"])
async def get_classes():
    """Liste des gestes reconnus"""
    if predictor.encoder is None:
        raise HTTPException(status_code=503, detail="Modèle non chargé")

    return {
        "classes": list(predictor.encoder.classes_),
        "count": len(predictor.encoder.classes_)
    }


@app.post("/predict", response_model=PredictionResponse, tags=["Prediction"])
async def predict(request: PredictionRequest):
    """
    Prédit le geste à partir des données du gant.

    - **data_points**: Liste de points temporels (séquence du geste)
    """
    if predictor.model is None:
        raise HTTPException(status_code=503, detail="Modèle non chargé")

    if len(request.data_points) == 0:
        raise HTTPException(status_code=400, detail="data_points vide")

    try:
        result = predictor.predict(request.data_points)
        return PredictionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))