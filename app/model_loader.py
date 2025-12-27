"""
Chargement du modèle et inférence LSF-Cam
"""

import numpy as np
import pickle
import tensorflow as tf
from tensorflow import keras
from pathlib import Path


# === Attention Layer Custom ===

class AttentionLayer(keras.layers.Layer):
    """Mécanisme d'attention (requis pour charger le modèle)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        self.W = self.add_weight(
            name='attention_weight',
            shape=(input_shape[-1], 1),
            initializer='glorot_uniform',
            trainable=True
        )
        self.b = self.add_weight(
            name='attention_bias',
            shape=(input_shape[1], 1),
            initializer='zeros',
            trainable=True
        )
        super().build(input_shape)

    def call(self, x):
        e = tf.nn.tanh(tf.tensordot(x, self.W, axes=1) + self.b)
        a = tf.nn.softmax(e, axis=1)
        return tf.reduce_sum(x * a, axis=1)

    def get_config(self):
        return super().get_config()


# === Classe Predictor ===

class LSFCamPredictor:
    """Gestionnaire de prédiction LSF-Cam"""

    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.model = None
        self.scaler = None
        self.encoder = None
        self.max_len = 150
        self.n_features = 22

    def load(self):
        """Charge le modèle et les préprocesseurs"""
        # Modèle
        model_path = self.models_dir / "final_model.keras"
        self.model = keras.models.load_model(
            model_path,
            custom_objects={'AttentionLayer': AttentionLayer}
        )

        # Scaler
        scaler_path = self.models_dir / "scaler.pkl"
        with open(scaler_path, 'rb') as f:
            self.scaler = pickle.load(f)

        # Label Encoder
        encoder_path = self.models_dir / "label_encoder.pkl"
        with open(encoder_path, 'rb') as f:
            self.encoder = pickle.load(f)

        return True

    def preprocess(self, data_points: list) -> np.ndarray:
        """Convertit les data_points en array normalisé"""
        sequence = []

        for dp in data_points:
            features = [
                # Main gauche (11 features)
                dp.left_hand.gyro['x'],
                dp.left_hand.gyro['y'],
                dp.left_hand.gyro['z'],
                dp.left_hand.accel['x'],
                dp.left_hand.accel['y'],
                dp.left_hand.accel['z'],
                *dp.left_hand.flex_sensors,
                # Main droite (11 features)
                dp.right_hand.gyro['x'],
                dp.right_hand.gyro['y'],
                dp.right_hand.gyro['z'],
                dp.right_hand.accel['x'],
                dp.right_hand.accel['y'],
                dp.right_hand.accel['z'],
                *dp.right_hand.flex_sensors,
            ]
            sequence.append(features)

        # Padding
        X = np.zeros((1, self.max_len, self.n_features))
        length = min(len(sequence), self.max_len)
        X[0, :length, :] = np.array(sequence[:length])

        # Normalisation
        X_flat = X.reshape(-1, self.n_features)
        X_scaled = self.scaler.transform(X_flat).reshape(X.shape)

        return X_scaled

    def predict(self, data_points: list) -> dict:
        """Effectue une prédiction"""
        # Preprocessing
        X = self.preprocess(data_points)

        # Inférence
        proba = self.model.predict(X, verbose=0)[0]

        # Résultat
        pred_idx = np.argmax(proba)
        confidence = float(proba[pred_idx])
        gesture = self.encoder.inverse_transform([pred_idx])[0]

        # Probabilités par classe
        probabilities = {
            cls: float(p)
            for cls, p in zip(self.encoder.classes_, proba)
        }

        return {
            'gesture': gesture,
            'confidence': confidence,
            'probabilities': probabilities
        }


# === Instance globale ===
predictor = LSFCamPredictor()