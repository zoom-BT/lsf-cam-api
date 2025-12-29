"""
Client API pour les prédictions LSF-Cam
"""

import requests
from typing import Optional, Dict, List, Tuple
import threading
from dataclasses import dataclass


@dataclass
class PredictionResult:
    gesture: str
    confidence: float
    probabilities: Dict[str, float]
    success: bool = True
    error: Optional[str] = None


class APIClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 30

    def set_base_url(self, url: str):
        """Met à jour l'URL de base de l'API"""
        self.base_url = url.rstrip('/')

    def check_health(self) -> Tuple[bool, str]:
        """Vérifie si l'API est accessible"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('model_loaded', False):
                    return True, "API connectée, modèle chargé"
                return True, "API connectée, modèle non chargé"
            return False, f"Erreur HTTP {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Impossible de se connecter à l'API"
        except requests.exceptions.Timeout:
            return False, "Timeout de connexion"
        except Exception as e:
            return False, str(e)

    def get_classes(self) -> List[str]:
        """Récupère la liste des classes disponibles"""
        try:
            response = requests.get(
                f"{self.base_url}/classes",
                timeout=5
            )
            if response.status_code == 200:
                return response.json().get('classes', [])
        except Exception:
            pass
        return []

    def predict(self, data_points: List[dict]) -> PredictionResult:
        """Envoie les données pour prédiction"""
        try:
            payload = {"data_points": data_points}

            response = requests.post(
                f"{self.base_url}/predict",
                json=payload,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return PredictionResult(
                    gesture=data['gesture'],
                    confidence=data['confidence'],
                    probabilities=data.get('probabilities', {})
                )
            else:
                return PredictionResult(
                    gesture="",
                    confidence=0.0,
                    probabilities={},
                    success=False,
                    error=f"Erreur HTTP {response.status_code}"
                )
        except requests.exceptions.ConnectionError:
            return PredictionResult(
                gesture="",
                confidence=0.0,
                probabilities={},
                success=False,
                error="Connexion à l'API impossible"
            )
        except requests.exceptions.Timeout:
            return PredictionResult(
                gesture="",
                confidence=0.0,
                probabilities={},
                success=False,
                error="Timeout de la requête"
            )
        except Exception as e:
            return PredictionResult(
                gesture="",
                confidence=0.0,
                probabilities={},
                success=False,
                error=str(e)
            )

    def predict_async(self, data_points: List[dict], callback):
        """Prédiction asynchrone avec callback"""

        def _predict():
            result = self.predict(data_points)
            callback(result)

        thread = threading.Thread(target=_predict, daemon=True)
        thread.start()
