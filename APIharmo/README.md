# 🚀 LSF-CMR API - Guide d'Utilisation

## 📋 Table des matières
- [Vue d'ensemble](#vue-densemble)
- [Installation](#installation)
- [Démarrage](#démarrage)
- [Utilisation de l'API](#utilisation-de-lapi)
- [Mise à jour du modèle depuis Kaggle](#mise-à-jour-du-modèle-depuis-kaggle)
- [Structure du projet](#structure-du-projet)
- [Dépannage](#dépannage)

---

## 🎯 Vue d'ensemble

L'API LSF-CMR est une API REST construite avec **FastAPI** qui permet de prédire des gestes de la Langue des Signes CMRerounaise à partir de données de capteurs provenant de gants ESP32.

### Architecture

```
┌──────────────┐     HTTP/JSON      ┌───────────────┐
│   Client     │ ◄────────────────► │   FastAPI     │
│ (LSF_CMRApp) │                     │      API      │
└──────────────┘                     └───────┬───────┘
                                             │
                                             ▼
                                     ┌───────────────┐
                                     │  TensorFlow   │
                                     │    Model      │
                                     └───────────────┘
```

### Technologies
- **FastAPI** : Framework web moderne et rapide
- **TensorFlow** : Modèle de deep learning (LSTM + Attention)
- **Pydantic** : Validation des données
- **Uvicorn** : Serveur ASGI

---

## 📦 Installation

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de packages Python)

### Étapes

1. **Naviguer vers le dossier API**
```bash
cd F:\Desktop\GI_manager\4GI\BigS1\Electronique\HarmoAI\APP\APIharmo
```

2. **Créer un environnement virtuel (recommandé)**
```bash
python -m venv venv
```

3. **Activer l'environnement virtuel**
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

4. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

---

## 🚀 Démarrage

### Méthode 1 : Avec Uvicorn (Recommandé)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Options :
- `--reload` : Redémarre automatiquement lors des modifications de code
- `--host 0.0.0.0` : Accessible depuis d'autres machines du réseau
- `--port 8000` : Port d'écoute (modifiable)

### Méthode 2 : Avec le script Python

```bash
python main.py
```

### Vérification

Une fois démarré, ouvrez votre navigateur à :
- **API** : http://localhost:8000
- **Documentation interactive** : http://localhost:8000/docs
- **Health check** : http://localhost:8000/health

---

## 🔌 Utilisation de l'API

### Endpoints disponibles

#### 1. **GET /** - Page d'accueil
```bash
curl http://localhost:8000/
```

Réponse :
```json
{
  "message": "LSF-CMR API",
  "docs": "/docs",
  "health": "/health"
}
```

#### 2. **GET /health** - Vérification de l'état
```bash
curl http://localhost:8000/health
```

Réponse :
```json
{
  "status": "ok",
  "model_loaded": true,
  "version": "1.0.0"
}
```

#### 3. **GET /classes** - Liste des gestes reconnus
```bash
curl http://localhost:8000/classes
```

Réponse :
```json
{
  "classes": ["0", "1", "2", "3", "A_1", "B_1", "C_1", ...],
  "count": 36
}
```

#### 4. **POST /predict** - Prédire un geste

**Format de la requête :**
```json
{
  "data_points": [
    {
      "left_hand": {
        "gyro": {"x": -70000, "y": 140000, "z": 1500},
        "accel": {"x": 8000, "y": -5000, "z": 16000},
        "flex_sensors": [100, 200, 300, 400, 500]
      },
      "right_hand": {
        "gyro": {"x": 500, "y": -66000, "z": 700},
        "accel": {"x": -17000, "y": 4000, "z": -1000},
        "flex_sensors": [50, 150, 250, 350, 450]
      }
    },
    // ... plus de points (jusqu'à 150)
  ]
}
```

**Exemple avec curl :**
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @test_samples.json
```

**Réponse :**
```json
{
  "gesture": "A_1",
  "confidence": 0.95,
  "probabilities": {
    "0": 0.001,
    "1": 0.002,
    "A_1": 0.95,
    "B_1": 0.03,
    ...
  }
}
```

### Utilisation depuis Python (Client)

```python
import requests

# Préparer les données
data = {
    "data_points": [
        {
            "left_hand": {
                "gyro": {"x": -70000, "y": 140000, "z": 1500},
                "accel": {"x": 8000, "y": -5000, "z": 16000},
                "flex_sensors": [100, 200, 300, 400, 500]
            },
            "right_hand": {
                "gyro": {"x": 500, "y": -66000, "z": 700},
                "accel": {"x": -17000, "y": 4000, "z": -1000},
                "flex_sensors": [50, 150, 250, 350, 450]
            }
        }
        # ... plus de points
    ]
}

# Appel API
response = requests.post("http://localhost:8000/predict", json=data)
result = response.json()

print(f"Geste prédit : {result['gesture']}")
print(f"Confiance : {result['confidence']:.2%}")
```

---

## 🔄 Mise à jour du modèle depuis Kaggle

### Étape 1 : Entraîner le modèle sur Kaggle

1. **Accéder à votre notebook Kaggle**
2. **Entraîner le modèle** (avec votre nouveau dataset)
3. **Sauvegarder les fichiers nécessaires** :

```python
# À la fin de votre notebook Kaggle

# 1. Sauvegarder le modèle
model.save('final_model.keras')

# 2. Sauvegarder le scaler
import pickle
with open('scaler.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# 3. Sauvegarder le label encoder
with open('label_encoder.pkl', 'wb') as f:
    pickle.dump(label_encoder, f)

# (Optionnel) Sauvegarder les métriques 
import matplotlib.pyplot as plt
plt.savefig('training_history.png')
plt.savefig('confusion_matrix.png')
```

### Étape 2 : Télécharger les fichiers depuis Kaggle

1. Dans Kaggle, cliquez sur **Output** dans le panneau de droite
2. Téléchargez les fichiers suivants :
   - `final_model.keras` ⚠️ **OBLIGATOIRE**
   - `scaler.pkl` ⚠️ **OBLIGATOIRE**
   - `label_encoder.pkl` ⚠️ **OBLIGATOIRE**
   - `training_history.png` (optionnel)
   - `confusion_matrix.png` (optionnel)

### Étape 3 : Remplacer les fichiers dans le dossier API

1. **Naviguer vers le dossier models**
```bash
cd F:\Desktop\GI_manager\4GI\BigS1\Electronique\HarmoAI\APP\APIharmo\models
```

2. **Sauvegarder l'ancien modèle (optionnel)**
```bash
mkdir backup_$(date +%Y%m%d)
copy *.keras backup_$(date +%Y%m%d)\
copy *.pkl backup_$(date +%Y%m%d)\
```

3. **Copier les nouveaux fichiers**
```bash
# Copier final_model.keras, scaler.pkl, label_encoder.pkl
# depuis votre dossier de téléchargements vers :
# F:\Desktop\GI_manager\4GI\BigS1\Electronique\HarmoAI\APP\APIharmo\models\
```

### Étape 4 : Redémarrer l'API

```bash
# Arrêter l'API (Ctrl+C)

# Redémarrer
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Étape 5 : Vérifier le nouveau modèle

```bash
# Tester le health check
curl http://localhost:8000/health

# Vérifier les classes
curl http://localhost:8000/classes

# Tester une prédiction
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d @test_samples.json
```

---

## 📁 Structure du projet

```
APIharmo/
├── app/
│   ├── __init__.py           # Package init
│   ├── main.py               # ⭐ Application FastAPI principale
│   ├── model_loader.py       # ⭐ Chargement modèle + inférence
│   └── schemas.py            # ⭐ Schémas Pydantic (validation)
│
├── models/                   # 📦 Fichiers du modèle
│   ├── final_model.keras     # ⚠️ OBLIGATOIRE - Modèle TensorFlow
│   ├── scaler.pkl            # ⚠️ OBLIGATOIRE - Normalisation
│   ├── label_encoder.pkl     # ⚠️ OBLIGATOIRE - Encodage labels
│   ├── training_history.png  # (Optionnel) Graphique d'entraînement
│   └── confusion_matrix.png  # (Optionnel) Matrice de confusion
│
├── main.py                   # Script de démarrage alternatif
├── requirements.txt          # ⭐ Dépendances Python
├── runtime.txt               # Version Python (pour déploiement)
├── test_samples.json         # Échantillons de test
├── test_all_classes.py       # Script de test
└── README.md                 # Ce fichier
```

### Fichiers importants

#### 📌 **app/main.py**
- Point d'entrée de l'API FastAPI
- Définit les endpoints (`/`, `/health`, `/classes`, `/predict`)
- Configure CORS pour accès depuis applications tierces

#### 📌 **app/model_loader.py**
- Classe `LSFCMRPredictor` pour gérer le modèle
- Méthode `preprocess()` : Convertit data_points → array normalisé
- Méthode `predict()` : Effectue l'inférence

#### 📌 **app/schemas.py**
- Définit les structures de données avec Pydantic
- `PredictionRequest` : Format d'entrée
- `PredictionResponse` : Format de sortie
- Validation automatique des données

#### 📌 **requirements.txt**
- Liste des dépendances Python
- Versions spécifiques pour compatibilité

---

## 🔍 Dépannage

### Problème : Erreur "Modèle non chargé"

**Symptôme :**
```json
{
  "detail": "Modèle non chargé"
}
```

**Solution :**
1. Vérifiez que les fichiers existent dans `models/` :
   - `final_model.keras`
   - `scaler.pkl`
   - `label_encoder.pkl`

2. Vérifiez les logs au démarrage :
```
Chargement du modèle...
Modèle chargé avec succès
```

### Problème : Erreur "data_points vide"

**Symptôme :**
```json
{
  "detail": "data_points vide"
}
```

**Solution :**
Assurez-vous que votre requête contient au moins 1 point :
```json
{
  "data_points": [
    { /* au moins un point ici */ }
  ]
}
```

### Problème : Erreur de validation Pydantic

**Symptôme :**
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "data_points", 0, "left_hand", "gyro", "x"],
      "msg": "Field required"
    }
  ]
}
```

**Solution :**
Vérifiez que chaque point contient toutes les clés requises :
- `left_hand` : `gyro` (x, y, z), `accel` (x, y, z), `flex_sensors` (5 valeurs)
- `right_hand` : `gyro` (x, y, z), `accel` (x, y, z), `flex_sensors` (5 valeurs)

### Problème : Port déjà utilisé

**Symptôme :**
```
ERROR: [Errno 10048] Only one usage of each socket address
```

**Solution :**
Changez le port :
```bash
uvicorn app.main:app --reload --port 8001
```

### Problème : TensorFlow trop lent

**Solution :**
Passez à `tensorflow` (GPU) au lieu de `tensorflow-cpu` :
```bash
pip uninstall tensorflow-cpu
pip install tensorflow
```

---

## 📊 Métriques du modèle actuel

- **Architecture** : BiLSTM + Attention Layer
- **Séquence max** : 150 time steps
- **Features** : 22 (11 par main)
- **Classes** : 36 gestes
- **Précision** : ~95% (sur dataset de test)

---

## 🔐 Sécurité

### En production :
1. **Désactiver le mode debug** :
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000  # Sans --reload
```

2. **Configurer CORS** pour autoriser uniquement votre domaine :
```python
# Dans app/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://votre-domaine.com"],  # Au lieu de "*"
    ...
)
```

3. **Ajouter une authentification** (API key, JWT, etc.)

---

## 📞 Support

Pour toute question ou problème :
- **Documentation** : http://localhost:8000/docs
- **Repo GitHub** : https://github.com/zoom-BT/lsf-cam-api
- **Contact** : tchoutzine@gmail.com

---

**Développé pour le projet LSF-CMR** 🤟
