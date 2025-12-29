import json
import os
import csv
from datetime import datetime
from typing import List, Dict, Optional
from collections import Counter

HISTORY_FILE = "prediction_history.json"


class HistoryManager:
    """Gère l'historique des prédictions"""

    def __init__(self, filename: str = HISTORY_FILE):
        self.filename = filename
        self.history: List[Dict] = []
        self.load()

    def load(self):
        """Charge l'historique depuis le fichier JSON"""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception as e:
                print(f"Erreur chargement historique: {e}")
                self.history = []

    def save(self):
        """Sauvegarde l'historique dans le fichier JSON"""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Erreur sauvegarde historique: {e}")
            return False

    def add_entry(self, gesture: str, confidence: float):
        """Ajoute une nouvelle entrée à l'historique"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "gesture": gesture,
            "confidence": round(confidence, 4)
        }
        self.history.append(entry)
        # Auto-save pour éviter de perdre des données en cas de crash
        self.save()
        return entry

    def get_entries(self, limit: int = 100) -> List[Dict]:
        """Récupère les dernières entrées"""
        return self.history[-limit:]

    def clear(self):
        """Efface l'historique"""
        self.history = []
        self.save()

    def export_csv(self, filepath: str) -> bool:
        """Exporte l'historique en CSV"""
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Heure", "Geste", "Confiance"])

                for entry in self.history:
                    dt = datetime.fromisoformat(entry["timestamp"])
                    writer.writerow([
                        dt.strftime("%Y-%m-%d"),
                        dt.strftime("%H:%M:%S"),
                        entry["gesture"],
                        f"{entry['confidence']:.2%}"
                    ])
            return True
        except Exception as e:
            print(f"Erreur export CSV: {e}")
            return False

    def get_stats(self) -> Dict:
        """Calcule les statistiques (gestes fréquents, confiance moyenne)"""
        if not self.history:
            return {
                "total_predictions": 0,
                "avg_confidence": 0.0,
                "top_gestures": []
            }

        total = len(self.history)
        avg_conf = sum(e["confidence"] for e in self.history) / total

        # Compter les gestes (sans le suffixe _1 si présent)
        gestures = [e["gesture"].replace("_1", "") for e in self.history]
        counts = Counter(gestures)

        return {
            "total_predictions": total,
            "avg_confidence": avg_conf,
            "top_gestures": counts.most_common(5)
        }
