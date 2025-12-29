"""
Schémas Pydantic pour validation des données API LSF-Cam
"""

from pydantic import BaseModel
from typing import List, Dict, Optional


# === ENTRÉE ===

class HandData(BaseModel):
    """Données d'une main (11 features)"""
    gyro: Dict[str, float]      # {"x": 0.0, "y": 0.0, "z": 0.0}
    accel: Dict[str, float]     # {"x": 0.0, "y": 0.0, "z": 0.0}
    flex_sensors: List[float]   # [5 valeurs]


class DataPoint(BaseModel):
    """Un point temporel (22 features)"""
    left_hand: HandData
    right_hand: HandData


class PredictionRequest(BaseModel):
    """Requête de prédiction"""
    data_points: List[DataPoint]  # Séquence temporelle


# === SORTIE ===

class PredictionResponse(BaseModel):
    """Réponse de prédiction"""
    gesture: str
    confidence: float
    probabilities: Optional[Dict[str, float]] = None


class HealthResponse(BaseModel):
    """Réponse health check"""
    status: str
    model_loaded: bool
    version: str