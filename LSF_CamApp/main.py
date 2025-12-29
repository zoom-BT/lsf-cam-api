"""
LSF-Cam Desktop Application
Application de reconnaissance de la Langue des Signes Camerounaise
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
import threading
import time
import json
import sys
from typing import List, Optional
import logging

# Import conditionnel pour le son (Windows uniquement)
try:
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("lsf_cam.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LSFCam")

from datetime import datetime
from collections import deque
from PIL import Image, ImageDraw
import pystray  # type: ignore

from config import Config
from websocket_client import WebSocketClient, MockWebSocketClient
from api_client import APIClient, PredictionResult
from tts_engine import TTSEngine
from history_manager import HistoryManager
from history_window import HistoryWindow
from sensor_visualizer import SensorVisualizerWindow

# Configuration du thème initiale (sera écrasée par la config chargée)
config_loader = Config()
ctk.set_appearance_mode(config_loader.get("theme_mode", "dark"))
ctk.set_default_color_theme(config_loader.get("color_theme", "blue"))
del config_loader


class WorkflowStep(ctk.CTkFrame):
    """Composant pour afficher une étape du workflow"""

    STATES = {
        'idle': {'color': '#555555', 'text': '○'},
        'active': {'color': '#FFD700', 'text': '◉'},
        'done': {'color': '#00FF00', 'text': '✓'},
        'error': {'color': '#FF4444', 'text': '✗'}
    }

    def __init__(self, parent, text: str, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.state = 'idle'

        self.indicator = ctk.CTkLabel(
            self,
            text=self.STATES['idle']['text'],
            font=("Arial", 16),
            text_color=self.STATES['idle']['color'],
            width=30
        )
        self.indicator.pack(side="left", padx=(0, 5))

        self.label = ctk.CTkLabel(
            self,
            text=text,
            font=("Arial", 12),
            text_color="#AAAAAA"
        )
        self.label.pack(side="left")

    def set_state(self, state: str):
        """Change l'état de l'étape"""
        if state in self.STATES:
            self.state = state
            self.indicator.configure(
                text=self.STATES[state]['text'],
                text_color=self.STATES[state]['color']
            )
            if state == 'active':
                self.label.configure(text_color="#FFFFFF")
            elif state == 'done':
                self.label.configure(text_color="#00FF00")
            elif state == 'error':
                self.label.configure(text_color="#FF4444")
            else:
                self.label.configure(text_color="#AAAAAA")


class SettingsWindow(ctk.CTkToplevel):
    """Fenêtre des paramètres"""

    def __init__(self, parent, config: Config, on_save=None):
        super().__init__(parent)

        self.config = config
        self.on_save = on_save

        self.title("Paramètres")
        self.geometry("400x500")
        self.resizable(False, False)

        # Centrer la fenêtre
        self.transient(parent)
        self.grab_set()

        self._create_widgets()

    def _create_widgets(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Titre
        title = ctk.CTkLabel(
            main_frame,
            text="⚙️ Configuration",
            font=("Arial", 18, "bold")
        )
        title.pack(pady=(0, 20))

        # ESP32 IP
        esp_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        esp_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(esp_frame, text="IP ESP32:", width=120, anchor="w").pack(side="left")
        self.esp_ip_entry = ctk.CTkEntry(esp_frame, width=200)
        self.esp_ip_entry.insert(0, self.config.get('esp32_ip'))
        self.esp_ip_entry.pack(side="left", padx=5)

        # ESP32 Port
        port_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        port_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(port_frame, text="Port ESP32:", width=120, anchor="w").pack(side="left")
        self.esp_port_entry = ctk.CTkEntry(port_frame, width=200)
        self.esp_port_entry.insert(0, str(self.config.get('esp32_port')))
        self.esp_port_entry.pack(side="left", padx=5)

        # API URL
        api_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        api_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(api_frame, text="URL API:", width=120, anchor="w").pack(side="left")
        self.api_url_entry = ctk.CTkEntry(api_frame, width=200)
        self.api_url_entry.insert(0, self.config.get('api_url'))
        self.api_url_entry.pack(side="left", padx=5)

        # Min data points
        min_dp_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        min_dp_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(min_dp_frame, text="Min. points:", width=120, anchor="w").pack(side="left")
        self.min_dp_entry = ctk.CTkEntry(min_dp_frame, width=200)
        self.min_dp_entry.insert(0, str(self.config.get('min_data_points')))
        self.min_dp_entry.pack(side="left", padx=5)

        # TTS Rate
        tts_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        tts_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(tts_frame, text="Vitesse TTS:", width=120, anchor="w").pack(side="left")
        self.tts_rate_slider = ctk.CTkSlider(tts_frame, from_=50, to=300, width=200)
        self.tts_rate_slider.set(self.config.get('tts_rate'))
        self.tts_rate_slider.pack(side="left", padx=5)

        # Info voix TTS
        voice_info_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        voice_info_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            voice_info_frame,
            text="ℹ️ La voix française la plus élégante disponible est automatiquement sélectionnée",
            font=("Arial", 9),
            text_color="#888888",
            wraplength=350
        ).pack(pady=5)

        # Realtime Interval
        rt_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        rt_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(rt_frame, text="Intervalle TR (s):", width=120, anchor="w").pack(side="left")
        self.rt_interval_entry = ctk.CTkEntry(rt_frame, width=200)
        self.rt_interval_entry.insert(0, str(self.config.get('realtime_interval')))
        self.rt_interval_entry.pack(side="left", padx=5)

        # Theme Mode
        theme_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        theme_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(theme_frame, text="Apparence:", width=120, anchor="w").pack(side="left")
        self.theme_mode_menu = ctk.CTkOptionMenu(theme_frame, values=["System", "Dark", "Light"], width=200)
        self.theme_mode_menu.set(self.config.get("theme_mode").capitalize())
        self.theme_mode_menu.pack(side="left", padx=5)

        # Color Theme
        color_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        color_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(color_frame, text="Couleur*:", width=120, anchor="w").pack(side="left")
        self.color_theme_menu = ctk.CTkOptionMenu(color_frame, values=["blue", "green", "dark-blue"], width=200)
        self.color_theme_menu.set(self.config.get("color_theme"))
        self.color_theme_menu.pack(side="left", padx=5)

        ctk.CTkLabel(main_frame, text="* Redémarrage requis pour la couleur", font=("Arial", 10),
                     text_color="gray").pack()

        # Boutons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(30, 0))

        ctk.CTkButton(
            btn_frame,
            text="Annuler",
            command=self.destroy,
            fg_color="#555555",
            width=100
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Sauvegarder",
            command=self._save,
            fg_color="#00AA00",
            width=100
        ).pack(side="right", padx=5)

    def _save(self):
        """Sauvegarde les paramètres"""
        try:
            self.config.set('esp32_ip', self.esp_ip_entry.get())
            self.config.set('esp32_port', int(self.esp_port_entry.get()))
            self.config.set('api_url', self.api_url_entry.get())
            self.config.set('min_data_points', int(self.min_dp_entry.get()))
            self.config.set('tts_rate', int(self.tts_rate_slider.get()))
            self.config.set('realtime_interval', float(self.rt_interval_entry.get()))

            # Thèmes
            new_mode = self.theme_mode_menu.get().lower()
            self.config.set('theme_mode', new_mode)
            ctk.set_appearance_mode(new_mode)

            self.config.set('color_theme', self.color_theme_menu.get())

            if self.on_save:
                self.on_save()

            self.destroy()
        except ValueError as e:
            messagebox.showerror("Erreur", f"Valeur invalide: {e}")


class LSFCamApp(ctk.CTk):
    """Application principale LSF-Cam"""

    def __init__(self):
        super().__init__()

        # Configuration
        self.config = Config()
        self.history = HistoryManager()

        # Composants
        self.ws_client: Optional[WebSocketClient] = None
        self.api_client = APIClient(self.config.get('api_url'))
        self.tts_engine = TTSEngine(
            rate=self.config.get('tts_rate'),
            volume=self.config.get('tts_volume')
        )

        # État
        self.is_recording = False
        self.is_realtime = False
        self.last_predict_time = 0
        self.realtime_buffer = deque(maxlen=self.config.get('realtime_buffer_size'))
        self.visualizer: Optional[SensorVisualizerWindow] = None
        self.tray_icon = None
        self.connection_attempted = False  # Indique si une connexion a été tentée

        self.data_points: List[dict] = []
        self.current_prediction: Optional[PredictionResult] = None
        self.sentence_buffer: List[str] = []

        # Configuration fenêtre
        self.title("🤟 LSF-Cam - Langue des Signes Camerounaise")
        self.geometry("800x700")
        self.minsize(700, 600)

        # Icône fenêtre (si fichier existe)
        # self.iconbitmap("icon.ico")

        # Créer l'interface
        self._create_ui()

        # Systray
        self._setup_systray()

        # Démarrer les services
        self.tts_engine.start()
        self._check_api_status()

        # Initialiser les raccourcis clavier
        self._bind_shortcuts()

        # Bind fermeture
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """Crée l'interface utilisateur"""

        # === HEADER ===
        header_frame = ctk.CTkFrame(self, height=60, corner_radius=0)
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        header_frame.pack_propagate(False)

        # Logo et titre
        title_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_frame.pack(side="left", padx=10)

        ctk.CTkLabel(
            title_frame,
            text="🤟 LSF-Cam",
            font=("Arial", 24, "bold"),
            text_color="#00BFFF"
        ).pack(side="left")

        # Statut connexion ESP32
        self.esp_status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.esp_status_frame.pack(side="left", padx=30)

        self.esp_icon = ctk.CTkLabel(
            self.esp_status_frame,
            text="📡",
            font=("Arial", 16)
        )
        self.esp_icon.pack(side="left")

        self.esp_status_label = ctk.CTkLabel(
            self.esp_status_frame,
            text="ESP32: Déconnecté",
            font=("Arial", 12),
            text_color="#FF4444"
        )
        self.esp_status_label.pack(side="left", padx=5)

        # Statut connexion API
        self.api_status_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.api_status_frame.pack(side="left", padx=20)

        self.api_icon = ctk.CTkLabel(
            self.api_status_frame,
            text="🌐",
            font=("Arial", 16)
        )
        self.api_icon.pack(side="left")

        self.api_status_label = ctk.CTkLabel(
            self.api_status_frame,
            text="API: Vérification...",
            font=("Arial", 12),
            text_color="#FFD700"
        )
        self.api_status_label.pack(side="left", padx=5)

        # Bouton paramètres
        settings_btn = ctk.CTkButton(
            header_frame,
            text="⚙️",
            width=40,
            height=40,
            command=self._open_settings,
            fg_color="#333333",
            hover_color="#444444"
        )
        settings_btn.pack(side="right", padx=10)

        # Bouton Historique
        history_btn = ctk.CTkButton(
            header_frame,
            text="📜",
            width=40,
            height=40,
            command=self._open_history,
            fg_color="#333333",
            hover_color="#444444"
        )
        history_btn.pack(side="right", padx=5)

        # Bouton Graphiques
        graph_btn = ctk.CTkButton(
            header_frame,
            text="📈",
            width=40,
            height=40,
            command=self._open_visualizer,
            fg_color="#333333",
            hover_color="#444444"
        )
        graph_btn.pack(side="right", padx=5)

        # === ZONE D'AFFICHAGE PRINCIPALE ===
        display_frame = ctk.CTkFrame(self, corner_radius=15)
        display_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Écran de visualisation
        self.display_screen = ctk.CTkFrame(
            display_frame,
            fg_color="#1a1a2e",
            corner_radius=10,
            height=250
        )
        self.display_screen.pack(fill="both", expand=True, padx=15, pady=15)

        # Geste reconnu (grand)
        self.gesture_label = ctk.CTkLabel(
            self.display_screen,
            text="—",
            font=("Arial", 120, "bold"),
            text_color="#00FFAA"
        )
        self.gesture_label.pack(expand=True)

        # Confiance
        self.confidence_label = ctk.CTkLabel(
            self.display_screen,
            text="Confiance: —",
            font=("Arial", 18),
            text_color="#888888"
        )
        self.confidence_label.pack(pady=(0, 10))

        # Phrase construite
        sentence_frame = ctk.CTkFrame(display_frame, fg_color="#0d0d1a", corner_radius=8)
        sentence_frame.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(
            sentence_frame,
            text="Phrase:",
            font=("Arial", 12),
            text_color="#666666"
        ).pack(side="left", padx=10, pady=8)

        self.sentence_label = ctk.CTkLabel(
            sentence_frame,
            text="",
            font=("Arial", 16),
            text_color="#FFFFFF",
            anchor="w"
        )
        self.sentence_label.pack(side="left", fill="x", expand=True, padx=5, pady=8)

        # Menu export avec sélection
        export_container = ctk.CTkFrame(sentence_frame, fg_color="transparent")
        export_container.pack(side="right", padx=10, pady=8)

        # Bouton effacer la phrase
        ctk.CTkButton(
            export_container,
            text="🗑️",
            width=30,
            height=28,
            font=("Arial", 14),
            fg_color="#AA0000",
            hover_color="#CC0000",
            command=self._clear_sentence
        ).pack(side="left", padx=2)

        ctk.CTkLabel(
            export_container,
            text="Exporter:",
            font=("Arial", 10),
            text_color="#888888"
        ).pack(side="left", padx=(5, 5))

        self.export_menu = ctk.CTkOptionMenu(
            export_container,
            values=["Phrase (TXT)", "Phrase (JSON)", "Phrase (CSV)", "Audio (WAV)"],
            width=130,
            height=28,
            font=("Arial", 11),
            fg_color="#444444",
            button_color="#555555",
            button_hover_color="#666666",
            command=self._on_export_selection
        )
        self.export_menu.set("Sélectionner")
        self.export_menu.pack(side="left")

        # === WORKFLOW ANIMÉ ===
        workflow_frame = ctk.CTkFrame(self, fg_color="transparent")
        workflow_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkLabel(
            workflow_frame,
            text="Workflow:",
            font=("Arial", 12, "bold"),
            text_color="#888888"
        ).pack(anchor="w")

        steps_frame = ctk.CTkFrame(workflow_frame, fg_color="transparent")
        steps_frame.pack(fill="x", pady=5)

        self.workflow_steps = {
            'connect': WorkflowStep(steps_frame, "Connexion ESP32"),
            'record': WorkflowStep(steps_frame, "Enregistrement"),
            'send': WorkflowStep(steps_frame, "Envoi API"),
            'predict': WorkflowStep(steps_frame, "Prédiction"),
            'speak': WorkflowStep(steps_frame, "Synthèse vocale")
        }

        for step in self.workflow_steps.values():
            step.pack(side="left", padx=15)

        # === STATISTIQUES ===
        stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=5)

        # Nombre de points
        self.points_label = ctk.CTkLabel(
            stats_frame,
            text="Points: 0",
            font=("Arial", 12),
            text_color="#888888"
        )
        self.points_label.pack(side="left", padx=20)

        # Barre de progression
        self.progress_bar = ctk.CTkProgressBar(stats_frame, width=200)
        self.progress_bar.pack(side="left", padx=10)
        self.progress_bar.set(0)

        # Top 3 prédictions
        self.top_predictions_label = ctk.CTkLabel(
            stats_frame,
            text="",
            font=("Arial", 11),
            text_color="#666666"
        )
        self.top_predictions_label.pack(side="right", padx=20)

        # === BOUTONS DE CONTRÔLE ===
        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=15)

        # Disposition en grille comme une console
        btn_grid = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_grid.pack()

        # Ligne du haut: Record, TTS, Stop
        top_row = ctk.CTkFrame(btn_grid, fg_color="transparent")
        top_row.pack(pady=5)

        # Bouton Record
        self.record_btn = ctk.CTkButton(
            top_row,
            text="⏺️ REC",
            width=100,
            height=50,
            font=("Arial", 14, "bold"),
            fg_color="#AA0000",
            hover_color="#CC0000",
            command=self._start_recording
        )
        self.record_btn.pack(side="left", padx=10)

        # Bouton TTS (central, plus grand)
        self.tts_btn = ctk.CTkButton(
            top_row,
            text="🔊",
            width=80,
            height=80,
            font=("Arial", 30),
            fg_color="#006699",
            hover_color="#0088CC",
            corner_radius=40,
            command=self._speak_result
        )
        self.tts_btn.pack(side="left", padx=20)

        # Bouton Stop
        self.stop_btn = ctk.CTkButton(
            top_row,
            text="⏹️ STOP",
            width=100,
            height=50,
            font=("Arial", 14, "bold"),
            fg_color="#555555",
            hover_color="#666666",
            command=self._stop_recording,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=10)

        # Ligne du bas: Predict, Reset
        bottom_row = ctk.CTkFrame(btn_grid, fg_color="transparent")
        bottom_row.pack(pady=10)

        # Bouton Predict
        self.predict_btn = ctk.CTkButton(
            bottom_row,
            text="▶️ Prédire",
            width=120,
            height=45,
            font=("Arial", 14, "bold"),
            fg_color="#008800",
            hover_color="#00AA00",
            command=self._predict,
            state="disabled"
        )
        self.predict_btn.pack(side="left", padx=10)

        # Bouton Reset
        self.reset_btn = ctk.CTkButton(
            bottom_row,
            text="🔄 Reset",
            width=100,
            height=45,
            font=("Arial", 14),
            fg_color="#666600",
            hover_color="#888800",
            command=self._reset
        )
        self.reset_btn.pack(side="left", padx=10)

        # Bouton connexion ESP32
        self.connect_btn = ctk.CTkButton(
            bottom_row,
            text="📡 Connecter",
            width=120,
            height=45,
            font=("Arial", 14),
            fg_color="#004466",
            hover_color="#006688",
            command=self._toggle_connection
        )
        self.connect_btn.pack(side="left", padx=10)

        # Mode test (sans ESP32)
        test_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        test_frame.pack(pady=(10, 0))

        self.mock_var = ctk.BooleanVar(value=False)
        self.mock_check = ctk.CTkCheckBox(
            test_frame,
            text="Mode Test (sans ESP32)",
            variable=self.mock_var,
            font=("Arial", 11, "bold"),
            text_color="#FFD700",
            command=self._on_mock_toggle
        )
        self.mock_check.pack(side="left", padx=5)

        ctk.CTkLabel(
            test_frame,
            text="ℹ️ Données simulées pour tests",
            font=("Arial", 9),
            text_color="#666666"
        ).pack(side="left", padx=5)

        # Switch Temps Réel
        self.realtime_switch = ctk.CTkSwitch(
            control_frame,
            text="Mode Temps Réel",
            command=self._toggle_realtime,
            font=("Arial", 12, "bold"),
            progress_color="#00AA00"
        )
        self.realtime_switch.pack(pady=(10, 0))

    def _check_api_status(self):
        """Vérifie le statut de l'API périodiquement"""

        def check():
            connected, message = self.api_client.check_health()
            self.after(0, lambda: self._update_api_status(connected, message))

        thread = threading.Thread(target=check, daemon=True)
        thread.start()

        # Revérifier toutes les 30 secondes
        self.after(30000, self._check_api_status)

    def _update_api_status(self, connected: bool, message: str):
        """Met à jour l'affichage du statut API"""
        if connected:
            self.api_status_label.configure(
                text=f"API: ✓ Connectée",
                text_color="#00FF00"
            )
        else:
            self.api_status_label.configure(
                text=f"API: ✗ {message[:20]}",
                text_color="#FF4444"
            )

    def _toggle_connection(self):
        """Connecte ou déconnecte du gant ESP32"""
        if self.ws_client and self.ws_client.is_connected:
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        """Connecte au gant ESP32"""
        self.connection_attempted = True  # Marquer qu'une connexion a été tentée
        self.workflow_steps['connect'].set_state('active')

        # Choisir le bon client
        if self.mock_var.get():
            self.ws_client = MockWebSocketClient(self.config.websocket_url)
        else:
            self.ws_client = WebSocketClient(self.config.websocket_url)

        # Callbacks
        self.ws_client.on_connected = self._on_esp_connected
        self.ws_client.on_disconnected = self._on_esp_disconnected
        self.ws_client.on_data = self._on_data_received
        self.ws_client.on_error = self._on_ws_error

        self.ws_client.start()
        self.connect_btn.configure(text="⏳ Connexion...")

    def _disconnect(self):
        """Déconnecte du gant ESP32"""
        if self.ws_client:
            self.ws_client.stop()
            self.ws_client = None

    def _on_esp_connected(self):
        """Callback: ESP32 connecté"""
        self.after(0, lambda: self._update_esp_status(True))

    def _on_esp_disconnected(self):
        """Callback: ESP32 déconnecté"""
        self.after(0, lambda: self._update_esp_status(False))

    def _on_ws_error(self, error: str):
        """Callback: Erreur WebSocket"""
        # Ne pas afficher d'erreur en mode test (mock)
        if self.mock_var.get():
            return

        # Ne pas afficher d'erreur si aucune connexion n'a été tentée
        if not self.connection_attempted:
            return

        # Afficher l'erreur uniquement si l'utilisateur a activement tenté de se connecter
        self.after(0, lambda: self._show_error(f"Erreur WebSocket: {error}"))

    def _update_esp_status(self, connected: bool):
        """Met à jour l'affichage du statut ESP32"""
        if connected:
            # Afficher un message différent selon le mode
            if self.mock_var.get():
                self.esp_status_label.configure(
                    text="ESP32: 🧪 Mode Test",
                    text_color="#FFD700"
                )
            else:
                self.esp_status_label.configure(
                    text="ESP32: ✓ Connecté",
                    text_color="#00FF00"
                )
            self.connect_btn.configure(text="📡 Déconnecter", fg_color="#AA0000", hover_color="#CC0000")
            self.workflow_steps['connect'].set_state('done')
            self.record_btn.configure(state="normal")
        else:
            self.esp_status_label.configure(
                text="ESP32: ✗ Déconnecté",
                text_color="#FF4444"
            )
            self.connect_btn.configure(text="📡 Connecter", fg_color="#004466", hover_color="#006688")
            self.workflow_steps['connect'].set_state('idle')
            if not self.is_recording:
                self.record_btn.configure(state="disabled")

    def _on_data_received(self, data: dict):
        """Callback: Données reçues du gant"""
        # Alimenter le buffer temps réel
        self.realtime_buffer.append(data)

        # Mettre à jour le visualiseur si ouvert
        if self.visualizer and self.visualizer.winfo_exists():
            self.visualizer.update_data(data)

        # Gestion enregistrement manuel
        if self.is_recording:
            self.data_points.append(data)
            self.after(0, self._update_recording_ui)

        # Gestion temps réel
        if self.is_realtime:
            current_time = time.time()
            interval = self.config.get('realtime_interval')

            if (current_time - self.last_predict_time) > interval:
                if len(self.realtime_buffer) >= self.config.get('realtime_buffer_size'):
                    self.last_predict_time = current_time
                    # Copie du buffer pour prédiction
                    points = list(self.realtime_buffer)
                    self.api_client.predict_async(points, self._on_prediction_result)

    def _update_recording_ui(self):
        """Met à jour l'interface pendant l'enregistrement"""
        count = len(self.data_points)
        min_points = self.config.get('min_data_points')
        max_points = self.config.get('max_data_points')

        # Texte animé avec points
        dots = "." * ((count // 5) % 4)
        self.points_label.configure(
            text=f"Points: {count}{dots}",
            text_color="#00FFAA" if count >= min_points else "#888888"
        )

        # Barre de progression avec couleur dynamique
        progress = min(count / min_points, 1.0)
        self.progress_bar.set(progress)

        # Changer la couleur de la barre selon la progression
        if progress >= 1.0:
            self.progress_bar.configure(progress_color="#00FF00")
        elif progress >= 0.7:
            self.progress_bar.configure(progress_color="#FFD700")
        else:
            self.progress_bar.configure(progress_color="#1f6aa5")

        # Activer le bouton prédire si assez de points
        if count >= min_points:
            self.predict_btn.configure(state="normal", fg_color="#00AA00")

        # Arrêter automatiquement si max atteint
        if count >= max_points:
            self._stop_recording()

    def _start_recording(self):
        """Démarre l'enregistrement"""
        if not self.ws_client or not self.ws_client.is_connected:
            self._show_error("Veuillez d'abord connecter le gant ESP32")
            return

        if self.is_realtime:
            self._show_error("Désactivez le mode Temps Réel pour enregistrer manuellement")
            return

        self.is_recording = True
        self.data_points = []

        # UI
        self.record_btn.configure(state="disabled", fg_color="#550000")
        self.stop_btn.configure(state="normal")
        self.predict_btn.configure(state="disabled")
        self.gesture_label.configure(text="⏺️", text_color="#FF0000")
        self.confidence_label.configure(text="Enregistrement en cours...")

        # Workflow
        self.workflow_steps['record'].set_state('active')
        self.workflow_steps['send'].set_state('idle')
        self.workflow_steps['predict'].set_state('idle')
        self.workflow_steps['speak'].set_state('idle')

    def _stop_recording(self):
        """Arrête l'enregistrement"""
        self.is_recording = False

        # UI
        self.record_btn.configure(state="normal", fg_color="#AA0000")
        self.stop_btn.configure(state="disabled")

        count = len(self.data_points)
        min_points = self.config.get('min_data_points')

        if count >= min_points:
            self.predict_btn.configure(state="normal")
            self.gesture_label.configure(text="✓", text_color="#00FF00")
            self.confidence_label.configure(text=f"{count} points capturés - Prêt!")
            self.workflow_steps['record'].set_state('done')
        else:
            self.gesture_label.configure(text="⚠️", text_color="#FFD700")
            self.confidence_label.configure(
                text=f"Seulement {count}/{min_points} points - Réessayez"
            )
            self.workflow_steps['record'].set_state('error')

    def _predict(self):
        """Lance la prédiction"""
        if not self.data_points:
            self._show_error("Aucune donnée à prédire")
            return

        # UI
        self.predict_btn.configure(state="disabled")
        self.gesture_label.configure(text="⏳", text_color="#FFD700")
        self.confidence_label.configure(text="Analyse en cours...")

        # Workflow
        self.workflow_steps['send'].set_state('active')

        # Appel API asynchrone
        self.api_client.predict_async(self.data_points, self._on_prediction_result)

    def _on_prediction_result(self, result: PredictionResult):
        """Callback: Résultat de prédiction reçu"""
        self.after(0, lambda: self._display_prediction(result))

    def _display_prediction(self, result: PredictionResult):
        """Affiche le résultat de la prédiction"""
        self.current_prediction = result

        if result.success:
            # Afficher le geste avec animation
            display_gesture = result.gesture.replace("_1", "")

            # Animation de pulsation pour le geste
            self._animate_gesture_display(display_gesture)

            # Confiance avec couleur
            confidence_pct = result.confidence * 100
            if confidence_pct >= 90:
                color = "#00FF00"
                emoji = "✓"
            elif confidence_pct >= 70:
                color = "#FFD700"
                emoji = "⚡"
            else:
                color = "#FF8800"
                emoji = "⚠️"

            self.confidence_label.configure(
                text=f"{emoji} Confiance: {confidence_pct:.1f}%",
                text_color=color
            )

            # Top 3 prédictions
            sorted_probs = sorted(
                result.probabilities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
            top_text = " | ".join([
                f"{g.replace('_1', '')}: {p * 100:.1f}%"
                for g, p in sorted_probs
            ])
            self.top_predictions_label.configure(text=top_text)

            # Ajouter à la phrase
            self.sentence_buffer.append(result.gesture)
            sentence_display = " ".join([
                g.replace("_1", "") for g in self.sentence_buffer
            ])
            self.sentence_label.configure(text=sentence_display)

            # Workflow
            self.workflow_steps['send'].set_state('done')
            self.workflow_steps['predict'].set_state('done')

            # Son de succès si confiance élevée
            if confidence_pct >= 70:
                self._play_success_sound()

            # Notification Systray si fenêtre cachée
            if not self.winfo_viewable() and self.tray_icon:
                self.tray_icon.notify(
                    f"Geste détecté : {display_gesture} ({confidence_pct:.0f}%)",
                    "LSF-Cam"
                )

            # Prononcer automatiquement
            self._speak_result()

            # Sauvegarder dans l'historique
            self.history.add_entry(result.gesture, result.confidence)

        else:
            self.gesture_label.configure(text="❌", text_color="#FF4444")
            self.confidence_label.configure(
                text=f"Erreur: {result.error}",
                text_color="#FF4444"
            )
            self.workflow_steps['send'].set_state('error')
            self.workflow_steps['predict'].set_state('error')

        # Réactiver les boutons
        self.predict_btn.configure(state="normal")
        self.record_btn.configure(state="normal")

    def _speak_result(self):
        """Prononce le résultat"""
        if self.current_prediction and self.current_prediction.success:
            self.workflow_steps['speak'].set_state('active')

            self.tts_engine.speak_gesture(
                self.current_prediction.gesture,
                self.current_prediction.confidence
            )

            # Marquer comme fait après un délai
            self.after(1000, lambda: self.workflow_steps['speak'].set_state('done'))

    def _clear_sentence(self):
        """Efface uniquement la phrase construite"""
        self.sentence_buffer = []
        self.sentence_label.configure(text="")

    def _reset(self):
        """Réinitialise tout"""
        self.is_recording = False
        self.data_points = []
        self.current_prediction = None
        self.sentence_buffer = []

        # UI
        self.gesture_label.configure(
            text="—",
            text_color="#00FFAA",
            font=("Arial", 120, "bold")
        )
        self.confidence_label.configure(text="Confiance: —", text_color="#888888")
        self.sentence_label.configure(text="")
        self.points_label.configure(text="Points: 0", text_color="#888888")
        self.progress_bar.set(0)
        self.progress_bar.configure(progress_color="#1f6aa5")
        self.top_predictions_label.configure(text="")

        # Boutons
        self.record_btn.configure(state="normal", fg_color="#AA0000")
        self.stop_btn.configure(state="disabled")
        self.predict_btn.configure(state="disabled")

        # Workflow
        for step in self.workflow_steps.values():
            step.set_state('idle')

        if self.ws_client and self.ws_client.is_connected:
            self.workflow_steps['connect'].set_state('done')

    def _open_settings(self):
        """Ouvre la fenêtre des paramètres"""
        SettingsWindow(self, self.config, self._on_settings_saved)

    def _on_settings_saved(self):
        """Callback: Paramètres sauvegardés"""
        # Mettre à jour les clients
        self.api_client.set_base_url(self.config.get('api_url'))
        self.tts_engine.set_rate(self.config.get('tts_rate'))

        if self.ws_client:
            self.ws_client.set_url(self.config.websocket_url)

        # Mettre à jour la taille du buffer si changé
        new_size = self.config.get('realtime_buffer_size')
        if self.realtime_buffer.maxlen != new_size:
            self.realtime_buffer = deque(maxlen=new_size)

        self._check_api_status()

    def _on_mock_toggle(self):
        """Gère l'activation/désactivation du mode test"""
        if self.mock_var.get():
            # Mode test activé
            if self.ws_client and self.ws_client.is_connected:
                # Déconnecter si déjà connecté
                self._disconnect()
        else:
            # Mode normal activé
            if self.ws_client and self.ws_client.is_connected:
                # Déconnecter le mock si actif
                self._disconnect()

    def _toggle_realtime(self):
        """Active/Désactive le mode temps réel"""
        if self.realtime_switch.get():
            self.is_realtime = True
            self.record_btn.configure(state="disabled")
            self.stop_btn.configure(state="disabled")
            self.predict_btn.configure(state="disabled")
            self.confidence_label.configure(text="Mode Temps Réel Actif - Analyse...")
        else:
            self.is_realtime = False
            self.record_btn.configure(state="normal")
            # self.stop_btn.configure(state="disabled") # Déjà géré par _reset ou stop
            self.confidence_label.configure(text="Prêt")
            self._reset()

    def _play_success_sound(self):
        """Joue un son de succès (Windows uniquement)"""
        if HAS_SOUND and sys.platform == 'win32':
            try:
                # Son de notification Windows
                threading.Thread(
                    target=lambda: winsound.MessageBeep(winsound.MB_OK),
                    daemon=True
                ).start()
            except:
                pass

    def _animate_gesture_display(self, gesture: str):
        """Affiche le geste sans animation"""
        # Affichage direct sans animation
        self.gesture_label.configure(
            text=gesture,
            text_color="#00FFAA",
            font=("Arial", 120, "bold")
        )

    def _show_error(self, message: str):
        """Affiche un message d'erreur"""
        messagebox.showerror("Erreur", message)

    def _setup_systray(self):
        """Configure l'icône systray"""

        def create_image():
            # Générer une icône simple
            width = 64
            height = 64
            color1 = "#00BFFF"  # DeepSkyBlue
            color2 = "white"
            image = Image.new('RGB', (width, height), color1)
            dc = ImageDraw.Draw(image)
            dc.ellipse((16, 16, 48, 48), fill=color2)
            return image

        def on_open(icon, item):
            self.after(0, self.deiconify)

        def on_record(icon, item):
            self.after(0, self._start_recording)

        def on_quit(icon, item):
            self.after(0, self._quit_application)

        self.tray_icon = pystray.Icon(
            "LSF-CMR",
            create_image(),
            menu=pystray.Menu(
                pystray.MenuItem("Ouvrir", on_open, default=True),
                pystray.MenuItem("Enregistrer", on_record),
                pystray.MenuItem("Quitter", on_quit)
            )
        )
        # Lancer dans un thread
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _on_close(self):
        """Intercepte la fermeture pour minimiser"""
        # Demander confirmation pour quitter ou minimiser ?
        # Pour faire simple: Minimiser dans le tray
        self.withdraw()
        if self.tray_icon:
            self.tray_icon.notify("Application minimisée dans la barre des tâches", "LSF-Cam")

    def _quit_application(self):
        """Fermeture complète"""
        if self.tray_icon:
            self.tray_icon.stop()
        if self.ws_client:
            self.ws_client.stop()
        if self.visualizer:
            self.visualizer.is_running = False
            self.visualizer.destroy()
        self.tts_engine.stop()
        self.destroy()

    def _bind_shortcuts(self):
        """Lie les raccourcis clavier"""
        self.bind("<space>", self._on_space_shortcut)
        self.bind("<Return>", lambda e: self._predict() if self.predict_btn.cget("state") == "normal" else None)
        self.bind("r", lambda e: self._reset())
        self.bind("R", lambda e: self._reset())
        self.bind("s", lambda e: self._speak_result())
        self.bind("S", lambda e: self._speak_result())
        self.bind("<Control-s>", self._on_save_shortcut)
        self.bind("<Delete>", lambda e: self._clear_sentence())
        self.bind("<BackSpace>", lambda e: self._clear_sentence())
        self.bind("<Escape>", self._on_escape_shortcut)
        self.bind("<F1>", self._show_shortcuts_help)

    def _on_space_shortcut(self, event=None):
        """Gestion touche Espace"""
        # Ignorer si le focus est sur un champ texte (ex: paramétrage)
        widget = self.focus_get()
        if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox)):
            return

        if self.is_recording:
            self._stop_recording()
        else:
            if self.record_btn.cget("state") == "normal":
                self._start_recording()

    def _on_save_shortcut(self, event=None):
        """Gestion Ctrl+S (Sauvegarde historique)"""
        if self.history.save():
            # Petit feedback visuel ou console
            print("Historique sauvegardé avec succès")
            # Optionnel: afficher un petit popup temporaire (toast)

    def _open_history(self):
        """Ouvre la fenêtre d'historique"""
        HistoryWindow(self, self.history)

    def _open_visualizer(self):
        """Ouvre la fenêtre de visualisation des capteurs"""
        if self.visualizer is None or not self.visualizer.winfo_exists():
            self.visualizer = SensorVisualizerWindow(self)
        else:
            self.visualizer.focus()

    def _on_escape_shortcut(self, event=None):
        """Gestion Echap"""
        if self.is_recording:
            self._stop_recording()
            return

        # Si une fenêtre modale est ouverte (Settings ou Shortcuts), elle se fermera d'elle-même
        # Ici on pourrait ajouter une confirmation de sortie si on le souhaite

    def _on_export_selection(self, choice: str):
        """Gère la sélection d'export depuis le menu"""
        if choice == "Sélectionner":
            return

        # Réinitialiser le menu après la sélection
        self.after(100, lambda: self.export_menu.set("Sélectionner"))

        if "Audio" in choice:
            self._export_audio()
        elif "JSON" in choice:
            self._export_sentence_format("json")
        elif "CSV" in choice:
            self._export_sentence_format("csv")
        elif "TXT" in choice:
            self._export_sentence_format("txt")

    def _export_sentence_format(self, format_type: str):
        """Exporte la phrase dans le format spécifié"""
        if not self.sentence_buffer:
            self._show_error("Aucune phrase à exporter")
            return

        text = " ".join([g.replace("_1", "") for g in self.sentence_buffer])
        if not text:
            return

        # Définir l'extension et le type de fichier
        extensions = {
            "txt": (".txt", "Fichier Texte"),
            "json": (".json", "Fichier JSON"),
            "csv": (".csv", "Fichier CSV")
        }
        ext, filetype = extensions.get(format_type, (".txt", "Fichier Texte"))

        filename = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(filetype, f"*{ext}")],
            title=f"Exporter Phrase ({format_type.upper()})"
        )

        if filename:
            try:
                if format_type == "json":
                    # Export JSON avec métadonnées
                    data = {
                        "timestamp": datetime.now().isoformat(),
                        "sentence": text,
                        "gestures": [g.replace("_1", "") for g in self.sentence_buffer],
                        "raw_gestures": self.sentence_buffer
                    }
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                elif format_type == "csv":
                    # Export CSV
                    import csv
                    with open(filename, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(["Position", "Geste"])
                        for i, gesture in enumerate([g.replace("_1", "") for g in self.sentence_buffer], 1):
                            writer.writerow([i, gesture])
                        writer.writerow([])
                        writer.writerow(["Phrase complète", text])

                else:  # txt
                    # Export TXT simple
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(f"Phrase LSF-Cam\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"\n{text}\n")

                messagebox.showinfo("Export Phrase", f"Phrase sauvegardée:\n{filename}")
            except Exception as e:
                self._show_error(f"Erreur lors de l'export: {e}")

    def _export_audio(self):
        """Exporte la phrase actuelle en fichier audio"""
        if not self.sentence_buffer:
            self._show_error("Aucune phrase à exporter")
            return

        text = " ".join([g.replace("_1", "") for g in self.sentence_buffer])
        if not text:
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".wav",
            filetypes=[("Fichier Audio WAV", "*.wav")],
            title="Exporter Audio"
        )

        if filename:
            self.tts_engine.save_to_file(text, filename)
            messagebox.showinfo("Export Audio", f"Fichier sauvegardé:\n{filename}")

    def _show_shortcuts_help(self, event=None):
        """Affiche la fenêtre d'aide des raccourcis"""
        help_window = ctk.CTkToplevel(self)
        help_window.title("Raccourcis Clavier")
        help_window.geometry("400x450")
        help_window.resizable(False, False)
        help_window.transient(self)
        help_window.grab_set()

        # Titre
        ctk.CTkLabel(
            help_window,
            text="⌨️ Raccourcis Clavier",
            font=("Arial", 18, "bold")
        ).pack(pady=20)

        # Liste des raccourcis
        shortcuts = [
            ("Espace", "Démarrer / Arrêter enregistrement"),
            ("Entrée", "Lancer la prédiction"),
            ("R", "Réinitialiser (Reset)"),
            ("S", "Prononcer le résultat (TTS)"),
            ("Suppr / ⌫", "Effacer la phrase"),
            ("Ctrl + S", "Sauvegarder l'historique"),
            ("Échap", "Arrêter enregistrement / Fermer"),
            ("F1", "Afficher cette aide")
        ]

        frame = ctk.CTkFrame(help_window, fg_color="transparent")
        frame.pack(fill="x", padx=30, pady=10)

        for key, desc in shortcuts:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", pady=8)

            # Touche (Key) - Style "Kbd"
            key_container = ctk.CTkFrame(row, fg_color="#444444", corner_radius=6, width=80)
            key_container.pack(side="left")
            key_container.pack_propagate(False)  # Garder la largeur fixe

            ctk.CTkLabel(
                key_container,
                text=key,
                font=("Arial", 12, "bold"),
                text_color="#FFFFFF"
            ).pack(expand=True)

            # Description
            ctk.CTkLabel(
                row,
                text=desc,
                font=("Arial", 12),
                text_color="#AAAAAA",
                anchor="w"
            ).pack(side="left", padx=15, fill="x", expand=True)

        # Bouton fermer
        ctk.CTkButton(
            help_window,
            text="Fermer",
            command=help_window.destroy,
            width=100
        ).pack(pady=20)


class SplashScreen(ctk.CTkToplevel):
    """Écran de démarrage"""

    def __init__(self, root):
        super().__init__(root)
        self.overrideredirect(True)  # Pas de bordures

        # Dimensions
        w, h = 400, 300
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.configure(fg_color="#0d0d1a")

        # Logo text
        ctk.CTkLabel(
            self,
            text="🤟",
            font=("Arial", 60)
        ).pack(pady=(50, 20))

        ctk.CTkLabel(
            self,
            text="LSF-Cam",
            font=("Arial", 30, "bold"),
            text_color="#00BFFF"
        ).pack()

        ctk.CTkLabel(
            self,
            text="Reconnaissance LSF Assistée par IA",
            font=("Arial", 12),
            text_color="#888888"
        ).pack(pady=10)

        self.progress = ctk.CTkProgressBar(self, width=200, mode="indeterminate")
        self.progress.pack(pady=20)
        self.progress.start()

        ctk.CTkLabel(
            self,
            text="Chargement des modules...",
            font=("Arial", 10),
            text_color="#666666"
        ).pack(side="bottom", pady=20)

        self.lift()
        self.focus_force()


def main():
    # Root caché pour gérer le splash
    root = ctk.CTk()
    root.withdraw()

    # Splash
    splash = SplashScreen(root)
    splash.update()

    # Simuler chargement (ou charger config lourde ici)
    # Dans une vraie app, on chargerait les modèles ici
    time.sleep(2)  # Juste pour l'effet visuel WOW

    # Lancer l'app principale
    app = LSFCamApp()

    # Fermer splash et montrer app
    splash.destroy()
    # root.destroy() # Non, car LSFCamApp hérite de CTk, donc c'est une root indépendante ?
    # LSFCamApp hérite de CTk, donc c'est une root. 
    # On ne peut pas avoir 2 roots facilement avec ctk.
    # Soluce: LSFCamApp doit être lancée seule. 
    # Le Splash peut être une fenêtre de LSFCamApp qui se ferme.

    # Approche corrigée:
    # LSFCamApp est la root. On la cache au début, on montre le splash, puis on swap.
    pass


# Réécriture de main() pour l'approche correcte
def main_corrected():
    app = LSFCamApp()
    app.withdraw()  # Cacher la main window

    splash = SplashScreen(app)

    def finish_loading():
        splash.destroy()
        app.deiconify()  # Montrer la main window

    app.after(2000, finish_loading)
    app.mainloop()


if __name__ == "__main__":
    main_corrected()
