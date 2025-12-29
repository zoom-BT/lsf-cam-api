"""
Configuration de l'application LSF-Cam
"""

import json
import os

CONFIG_FILE = "lsfcam_config.json"

DEFAULT_CONFIG = {
    "esp32_ip": "192.168.4.1",
    "esp32_port": 81,
    "api_url": "http://localhost:8000",
    "min_data_points": 50,
    "max_data_points": 150,
    "sample_rate_ms": 50,
    "language": "fr",
    "tts_rate": 150,
    "tts_volume": 1.0,
    "realtime_interval": 2.0,
    "realtime_buffer_size": 60,
    "theme_mode": "dark",
    "color_theme": "blue"
}


class Config:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Charge la configuration depuis le fichier"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    self.config.update(saved)
            except Exception as e:
                print(f"Erreur chargement config: {e}")

    def save(self):
        """Sauvegarde la configuration"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Erreur sauvegarde config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save()

    @property
    def websocket_url(self):
        return f"ws://{self.config['esp32_ip']}:{self.config['esp32_port']}"

    @property
    def api_predict_url(self):
        return f"{self.config['api_url']}/predict"

    @property
    def api_health_url(self):
        return f"{self.config['api_url']}/health"
