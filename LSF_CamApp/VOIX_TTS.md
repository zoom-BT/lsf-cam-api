# 🔊 Guide d'amélioration de la voix TTS

## Voix par défaut

L'application utilise automatiquement la meilleure voix française disponible sur votre système. Par défaut, Windows propose des voix de base qui peuvent sembler robotiques.

## 🎯 Comment obtenir une voix plus élégante ?

### Option 1: Voix Windows améliorées (Gratuit)

1. **Ouvrir les Paramètres Windows**
   - Appuyez sur `Win + I`
   - Allez dans `Heure et langue` > `Langue et région`

2. **Ajouter la langue française**
   - Cliquez sur `Ajouter une langue`
   - Recherchez `Français (France)`
   - Cochez `Synthèse vocale` et installez

3. **Télécharger les voix premium**
   - Dans `Paramètres` > `Accessibilité` > `Narrateur`
   - Cliquez sur `Ajouter des voix de synthèse vocale`
   - Téléchargez **Hortense** (voix féminine française de qualité)

### Option 2: eSpeak NG (Gratuit, Open Source)

Une alternative légère et performante :

```bash
# Installer eSpeak NG
pip install espeak-ng
```

### Option 3: Google Text-to-Speech (Nécessite connexion internet)

Pour une qualité professionnelle :

```bash
# Installer gTTS
pip install gtts pygame
```

**Note:** Cette option nécessite une modification du code pour utiliser gTTS au lieu de pyttsx3.

### Option 4: Azure Cognitive Services (Payant mais très haute qualité)

Microsoft Azure propose des voix neuronales ultra-réalistes :

1. Créer un compte Azure
2. Activer le service Speech
3. Installer le SDK : `pip install azure-cognitiveservices-speech`

**Voix recommandées:**
- `fr-FR-DeniseNeural` (Féminine, élégante)
- `fr-FR-HenriNeural` (Masculine, professionnelle)
- `fr-CA-SylvieNeural` (Accent canadien)

## 🎨 Réglages de la voix actuelle

Dans l'application, vous pouvez ajuster :

- **Vitesse** : Via le slider dans les paramètres (50-300)
- **Volume** : Géré automatiquement à 100%

### Vitesse recommandée par usage :

- **Lecture normale** : 150 (par défaut)
- **Lecture lente** : 100 (apprentissage)
- **Lecture rapide** : 200 (experts)

## 📋 Voix détectées sur votre système

Au démarrage de l'application, consultez la console pour voir la liste des voix disponibles :

```
=== Voix TTS disponibles ===
  - Microsoft Hortense Desktop - French (France)
  - Microsoft David Desktop - English (United States)
  - ...
===========================
```

## 🔧 Dépannage

### Problème : La voix ne fonctionne qu'une fois
✅ **Corrigé** : Le moteur TTS est maintenant réinitialisé avant chaque utilisation.

### Problème : Accent incorrect
- Vérifiez que vous avez installé la voix française dans Windows
- L'application sélectionne automatiquement la meilleure voix française

### Problème : Voix robotique
- Installez Hortense (voix Microsoft premium)
- Ou passez à Azure Neural Voices pour une qualité professionnelle

## 💡 Astuce

Pour une expérience optimale, nous recommandons :
1. Installer **Microsoft Hortense** (gratuit avec Windows)
2. Régler la vitesse à **150**
3. Tester avec le bouton 🔊 dans l'interface

---

**Développé pour LSF-Cam** 🤟
