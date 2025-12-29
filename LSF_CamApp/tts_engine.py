"""
Moteur Text-to-Speech pour LSF-Cam
"""

import pyttsx3
import threading
from typing import Optional
from queue import Queue


class TTSEngine:
    # Mapping des gestes vers le texte à prononcer
    GESTURE_SPEECH = {
        # Chiffres
        "0": "zéro",
        "1": "un",
        "2": "deux",
        "3": "trois",
        "4": "quatre",
        "5": "cinq",
        "6": "six",
        "7": "sept",
        "8": "huit",
        "9": "neuf",
        # Lettres (format X_1 -> X)
        "A_1": "A",
        "B_1": "B",
        "C_1": "C",
        "D_1": "D",
        "E_1": "E",
        "F_1": "F",
        "G_1": "G",
        "H_1": "H",
        "I_1": "I",
        "J_1": "J",
        "K_1": "K",
        "L_1": "L",
        "M_1": "M",
        "N_1": "N",
        "O_1": "O",
        "P_1": "P",
        "Q_1": "Q",
        "R_1": "R",
        "S_1": "S",
        "T_1": "T",
        "U_1": "U",
        "V_1": "V",
        "W_1": "W",
        "X_1": "X",
        "Y_1": "Y",
        "Z_1": "Z",
    }

    def __init__(self, rate: int = 150, volume: float = 1.0):
        self.engine = None
        self.rate = rate
        self.volume = volume
        self.speech_queue = Queue()
        self.is_running = False
        self.thread = None
        self._init_engine()

    def _init_engine(self):
        """Initialise le moteur TTS"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)

            # Rechercher la meilleure voix française disponible
            voices = self.engine.getProperty('voices')
            french_voice = None

            # Priorité 1: Voix française féminine (plus élégante)
            for voice in voices:
                if 'french' in voice.name.lower() or 'fr' in voice.id.lower():
                    if 'female' in voice.name.lower() or 'hortense' in voice.name.lower() or 'amelie' in voice.name.lower():
                        french_voice = voice.id
                        print(f"Voix TTS sélectionnée: {voice.name}")
                        break

            # Priorité 2: N'importe quelle voix française
            if not french_voice:
                for voice in voices:
                    if 'french' in voice.name.lower() or 'fr' in voice.id.lower():
                        french_voice = voice.id
                        print(f"Voix TTS sélectionnée: {voice.name}")
                        break

            # Priorité 3: Voix par défaut féminine
            if not french_voice:
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        french_voice = voice.id
                        print(f"Voix TTS par défaut: {voice.name}")
                        break

            if french_voice:
                self.engine.setProperty('voice', french_voice)

            # Afficher les voix disponibles pour information
            print("\n=== Voix TTS disponibles ===")
            for voice in voices:
                print(f"  - {voice.name} ({voice.id})")
            print("===========================\n")

        except Exception as e:
            print(f"Erreur initialisation TTS: {e}")
            self.engine = None

    def start(self):
        """Démarre le thread de lecture"""
        if self.is_running:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._speech_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Arrête le thread de lecture"""
        self.is_running = False
        if self.engine:
            self.engine.stop()

    def _speech_loop(self):
        """Boucle de lecture des messages"""
        import time

        while self.is_running:
            try:
                if not self.speech_queue.empty():
                    item = self.speech_queue.get()

                    # Rétro-compatibilité pour strings simples
                    if isinstance(item, str):
                        item = {"type": "SPEAK", "text": item}

                    if item["type"] == "SPEAK":
                        if self.engine:
                            try:
                                # Réinitialiser l'engine avant chaque utilisation (fix bug pyttsx3)
                                self.engine = pyttsx3.init()
                                self.engine.setProperty('rate', self.rate)
                                self.engine.setProperty('volume', self.volume)

                                # Configurer la voix française si disponible
                                voices = self.engine.getProperty('voices')
                                for voice in voices:
                                    if 'french' in voice.name.lower() or 'fr' in voice.id.lower():
                                        self.engine.setProperty('voice', voice.id)
                                        break

                                self.engine.say(item["text"])
                                self.engine.runAndWait()

                                # Nettoyer après utilisation
                                try:
                                    self.engine.stop()
                                    del self.engine
                                except:
                                    pass

                            except RuntimeError as e:
                                # Bug pyttsx3 : runAndWait appelé pendant qu'il tourne
                                print(f"Erreur runAndWait: {e}")
                                # Forcer l'arrêt et réinitialisation
                                try:
                                    self.engine.stop()
                                    del self.engine
                                except:
                                    pass
                                self._init_engine()

                    elif item["type"] == "SAVE":
                        if self.engine:
                            try:
                                # Réinitialiser pour le save aussi
                                self.engine = pyttsx3.init()
                                self.engine.setProperty('rate', self.rate)
                                self.engine.setProperty('volume', self.volume)

                                self.engine.save_to_file(item["text"], item["filename"])
                                self.engine.runAndWait()

                                # Nettoyer
                                try:
                                    self.engine.stop()
                                    del self.engine
                                except:
                                    pass

                            except RuntimeError as e:
                                print(f"Erreur SAVE runAndWait: {e}")
                                try:
                                    self.engine.stop()
                                    del self.engine
                                except:
                                    pass
                                self._init_engine()

            except Exception as e:
                print(f"Erreur TTS générale: {e}")
                # Réinitialiser le moteur en cas d'erreur
                try:
                    if self.engine:
                        self.engine.stop()
                        del self.engine
                except:
                    pass
                self._init_engine()

            time.sleep(0.1)

    def speak(self, text: str):
        """Ajoute du texte à la queue de lecture"""
        self.speech_queue.put({"type": "SPEAK", "text": text})

    def save_to_file(self, text: str, filename: str):
        """Sauvegarde le texte en fichier audio"""
        self.speech_queue.put({"type": "SAVE", "text": text, "filename": filename})

    def speak_gesture(self, gesture: str, confidence: Optional[float] = None):
        """Prononce le geste reconnu"""
        speech_text = self.GESTURE_SPEECH.get(gesture, gesture)

        if confidence is not None and confidence < 0.7:
            speech_text = f"Peut-être {speech_text}"

        self.speak(speech_text)

    def speak_sentence(self, gestures: list):
        """Prononce une séquence de gestes comme une phrase"""
        words = [self.GESTURE_SPEECH.get(g, g) for g in gestures]
        sentence = " ".join(words)
        self.speak(sentence)

    def set_rate(self, rate: int):
        """Change la vitesse de lecture"""
        self.rate = rate
        if self.engine:
            self.engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        """Change le volume (0.0 à 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.engine:
            self.engine.setProperty('volume', self.volume)

    def clear_queue(self):
        """Vide la queue de lecture"""
        while not self.speech_queue.empty():
            self.speech_queue.get()
