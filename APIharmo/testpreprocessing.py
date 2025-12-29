# test_preprocessing.py
import numpy as np
import pickle
import tensorflow as tf
from tensorflow import keras
import json

# Charger les fichiers
MODEL_DIR = "models"

# Charger scaler et encoder
with open(f'{MODEL_DIR}/scaler.pkl', 'rb') as f:
    scaler = pickle.load(f)

with open(f'{MODEL_DIR}/label_encoder.pkl', 'rb') as f:
    encoder = pickle.load(f)

print("Classes:", encoder.classes_)

# Données D_1 (premier data_point seulement pour test)
raw_data = {
    "left_hand": {
        "gyro": {"x": -490.0, "y": -178.0, "z": -127.0},
        "accel": {"x": 13704.0, "y": -10040.0, "z": 1892.0},
        "flex_sensors": [0, 1425, 1060, 1589, 2]
    },
    "right_hand": {
        "gyro": {"x": 964.0, "y": -868.0, "z": -136.0},
        "accel": {"x": -14488.0, "y": 6108.0, "z": -976.0},
        "flex_sensors": [69, 1253, 1400, 1173, 332]
    }
}

# Extraire features (même ordre que l'entraînement)
features = [
    raw_data['left_hand']['gyro']['x'],
    raw_data['left_hand']['gyro']['y'],
    raw_data['left_hand']['gyro']['z'],
    raw_data['left_hand']['accel']['x'],
    raw_data['left_hand']['accel']['y'],
    raw_data['left_hand']['accel']['z'],
    *raw_data['left_hand']['flex_sensors'],
    raw_data['right_hand']['gyro']['x'],
    raw_data['right_hand']['gyro']['y'],
    raw_data['right_hand']['gyro']['z'],
    raw_data['right_hand']['accel']['x'],
    raw_data['right_hand']['accel']['y'],
    raw_data['right_hand']['accel']['z'],
    *raw_data['right_hand']['flex_sensors'],
]

print(f"\nFeatures brutes ({len(features)}):")
print(features)

# Appliquer scaler sur un seul vecteur
features_array = np.array(features).reshape(1, -1)
features_scaled = scaler.transform(features_array)

print(f"\nFeatures après scaler:")
print(features_scaled[0])

print(f"\nScaler center (médiane):")
print(scaler.center_)

print(f"\nScaler scale (IQR):")
print(scaler.scale_)