# 🤟 LSF-Cam Application

Application de bureau pour la reconnaissance de la Langue des Signes Camerounaise (LSF) utilisant un gant connecté ESP32 et l'intelligence artificielle.

## 🚀 Fonctionnalités

### 🌟 Nouvelles Fonctionnalités (v2.1)

#### Corrections et améliorations critiques
- **✅ Bug TTS Corrigé** : La synthèse vocale fonctionne maintenant de manière fiable et continue
- **✅ Gestion WebSocket Améliorée** : Messages d'erreur plus clairs, timeout configuré, reconnexion automatique
- **✅ Code Optimisé** : Suppression des duplications, performances améliorées

#### Nouvelles fonctionnalités
- **📤 Export de Phrases** : Sauvegarde des phrases en TXT, JSON ou CSV avec métadonnées
- **🎨 Animations Élégantes** :
  - Animation de pulsation sur les gestes détectés
  - Barre de progression avec couleurs dynamiques
  - Effets visuels lors de l'enregistrement
- **🔔 Notifications Sonores** : Son de succès lors d'une prédiction avec haute confiance (Windows)
- **💎 Interface Améliorée** :
  - Emojis indicateurs de confiance (✓ ⚡ ⚠️)
  - Boutons d'export séparés (Phrase + Audio)
  - Workflow visuel animé et coloré

### Fonctionnalités v2.0

- **Mode Temps Réel** : Prédiction continue automatique sans intervention manuelle
- **Historique** : Sauvegarde automatique des prédictions, statistiques, et export CSV
- **Visualisation Capteurs** : Graphiques en temps réel (Gyroscope, Accéléromètre, Capteurs de flexion)
- **Synthèse Vocale** : Export audio en fichier WAV
- **Personnalisation** : Thèmes Clair/Sombre, couleur d'accentuation, et vitesse TTS configurables
- **Systray** : Minimisation dans la zone de notification, fonctionnement en arrière-plan
- **Raccourcis Clavier** : Navigation rapide et contrôle complet au clavier

### Fonctionnalités de base

- Connexion WebSocket avec le gant ESP32
- Interface moderne (CustomTkinter)
- Synthèse vocale (TTS) des gestes reconnus
- Construction de phrases
- API FastAPI pour les prédictions IA

## 🛠️ Installation

1. Assurez-vous d'avoir Python 3.9+ installé.
2. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
   ```
3. Lancez l'application :
   ```bash
   python main.py
   ```
   ou double-cliquez sur `run.bat`.

## ⌨️ Raccourcis Clavier

| Touche       | Action                                            |
|--------------|---------------------------------------------------|
| **Espace**   | Démarrer / Arrêter l'enregistrement (Mode Manuel) |
| **Entrée**   | Lancer la prédiction (si données capturées)       |
| **R**        | Réinitialiser (Reset)                             |
| **S**        | Prononcer le résultat (TTS)                       |
| **Ctrl + S** | Sauvegarder l'historique (Force Save)             |
| **Échap**    | Arrêter / Fermer / Minimiser                      |
| **F1**       | Afficher l'aide des raccourcis                    |

## 📁 Structure du Projet

- `main.py` : Point d'entrée et interface principale
- `config.py` : Gestion de la configuration (JSON)
- `websocket_client.py` : Communication avec l'ESP32
- `api_client.py` : Communication avec l'API de prédiction
- `tts_engine.py` : Moteur de synthèse vocale (corrigé v2.1)
- `history_manager.py` : Gestion de l'historique et stats
- `history_window.py` : Fenêtre de visualisation de l'historique
- `sensor_visualizer.py` : Fenêtre des graphiques matplotlib

## 🔧 Configuration

L'adresse IP de l'ESP32 et de l'API peuvent être configurées via le menu Paramètres (⚙️) ou directement dans `lsfcam_config.json`.

### Paramètres disponibles
- **esp32_ip** : Adresse IP du gant ESP32 (défaut: 192.168.4.1)
- **esp32_port** : Port WebSocket (défaut: 81)
- **api_url** : URL de l'API FastAPI (défaut: http://localhost:8000)
- **min_data_points** : Nombre minimum de points pour prédiction (défaut: 50)
- **tts_rate** : Vitesse de la synthèse vocale (défaut: 150)
- **realtime_interval** : Intervalle de prédiction en temps réel en secondes (défaut: 2.0)
- **theme_mode** : Thème de l'interface - "dark" ou "light" (défaut: dark)

## 🐛 Bugs Corrigés (v2.1)

1. **Synthèse vocale qui s'arrêtait après la première utilisation**
   - Cause : Exception `RuntimeError` non gérée dans pyttsx3
   - Solution : Gestion d'erreur robuste avec réinitialisation automatique du moteur

2. **Erreur WebSocket "timed out during opening handshake"**
   - Cause : Timeout par défaut trop court
   - Solution : Configuration explicite du timeout (15s) et messages d'erreur explicites

3. **Code dupliqué dans main.py**
   - Imports doublés, widgets créés deux fois
   - Solution : Nettoyage complet du code

## 📤 Formats d'Export

### Export de Phrase
- **TXT** : Format simple avec date et phrase
- **JSON** : Format structuré avec timestamp, gestes bruts et formatés
- **CSV** : Format tableur avec numérotation des gestes

### Export Audio
- **WAV** : Fichier audio de la phrase prononcée par le moteur TTS

## 🎯 Workflow d'Utilisation

1. **Connexion** : Cliquez sur "📡 Connecter" pour se connecter au gant ESP32
2. **Enregistrement** : Appuyez sur "⏺️ REC" ou Espace pour enregistrer un geste
3. **Prédiction** : Cliquez sur "▶️ Prédire" ou Entrée une fois assez de points capturés
4. **Synthèse** : Le geste est prononcé automatiquement et ajouté à la phrase
5. **Export** : Sauvegardez la phrase (💾 Phrase) ou l'audio (🔊 Audio)

### Mode Temps Réel
Activez le switch "Mode Temps Réel" pour une prédiction automatique continue sans intervention manuelle.

---
*Développé pour le projet HarmoAI - Version 2.1*
