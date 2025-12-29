"""
Script de test pour vérifier toutes les classes via l'API
Usage: python test_all_classes.py
"""

import requests
import json

# URL de l'API (local ou Render)
API_URL = "http://localhost:8000"  # Changer pour Render si besoin
# API_URL = "https://lsf-cam-api.onrender.com"

# Charger les échantillons de test
with open('test_samples.json', 'r') as f:
    test_samples = json.load(f)

print("=" * 60)
print("TEST DE TOUTES LES CLASSES")
print("=" * 60)

correct = 0
total = len(test_samples)

for label, data in test_samples.items():
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=data,
            timeout=30
        )
        result = response.json()
        
        predicted = result['gesture']
        confidence = result['confidence']
        
        status = "✅" if predicted == label else "❌"
        if predicted == label:
            correct += 1
        
        print(f"{status} {label:5} -> Prédit: {predicted:5} (confiance: {confidence:.2%})")
        
    except Exception as e:
        print(f"❌ {label:5} -> Erreur: {e}")

print("=" * 60)
print(f"Résultat: {correct}/{total} correct ({correct/total*100:.0f}%)")
print("=" * 60)
