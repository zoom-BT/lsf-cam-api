import customtkinter as ctk
import matplotlib
matplotlib.use('Agg')  # Backend non-bloquant
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from collections import deque
import numpy as np
import threading
import time


class SensorVisualizerWindow(ctk.CTkToplevel):
    """Fenêtre de visualisation des données capteurs en temps réel"""

    def __init__(self, parent, history_len=50):
        super().__init__(parent)

        self.title("Visualisation Capteurs")
        self.geometry("1000x800")

        self.parent = parent
        self.history_len = history_len
        self.is_running = True
        self.current_hand = "right_hand"  # ou "left_hand"

        # Données buffers
        self.gyro_x = deque(maxlen=history_len)
        self.gyro_y = deque(maxlen=history_len)
        self.gyro_z = deque(maxlen=history_len)

        self.accel_x = deque(maxlen=history_len)
        self.accel_y = deque(maxlen=history_len)
        self.accel_z = deque(maxlen=history_len)

        self.flex_vals = [0, 0, 0, 0, 0]

        # Initialisation UI
        self._create_ui()
        self._init_plots()

        # Démarrer la boucle de rafraîchissement
        self._animate()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        # Controls Header
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=10, pady=5)

        self.hand_switch = ctk.CTkSwitch(
            header,
            text="Main Droite / Main Gauche",
            command=self._toggle_hand,
            onvalue="left_hand",
            offvalue="right_hand"
        )
        self.hand_switch.pack(side="left", padx=20)

        ctk.CTkButton(
            header,
            text="Fermer",
            command=self._on_close,
            width=100
        ).pack(side="right", padx=20)

    def _init_plots(self):
        # Style sombre pour matplotlib
        plt.style.use('dark_background')

        # Création Figure et Subplots avec Figure au lieu de plt.Figure
        self.fig = Figure(figsize=(10, 8), dpi=100)
        self.fig.patch.set_facecolor('#1a1a2e')  # Couleur de fond CustomTkinter

        # Grid layout: 
        # ax1: Gyro (Top Left)
        # ax2: Accel (Bottom Left)
        # ax3: Flex (Right column full height)

        gs = self.fig.add_gridspec(2, 2)

        self.ax_gyro = self.fig.add_subplot(gs[0, 0])
        self.ax_accel = self.fig.add_subplot(gs[1, 0])
        self.ax_flex = self.fig.add_subplot(gs[:, 1])

        self._setup_ax(self.ax_gyro, "Gyroscope", "deg/s")
        self._setup_ax(self.ax_accel, "Accéléromètre", "m/s²")
        self._setup_ax(self.ax_flex, "Capteurs Flexion", "Valeur ADC")

        # Lignes initiales
        xs = list(range(self.history_len))
        zeros = [0] * self.history_len

        self.line_gx, = self.ax_gyro.plot(xs, zeros, label='X', color='#FF4444')
        self.line_gy, = self.ax_gyro.plot(xs, zeros, label='Y', color='#44FF44')
        self.line_gz, = self.ax_gyro.plot(xs, zeros, label='Z', color='#4444FF')
        self.ax_gyro.legend(loc='upper right', fontsize='small')

        self.line_ax, = self.ax_accel.plot(xs, zeros, label='X', color='#FF4444')
        self.line_ay, = self.ax_accel.plot(xs, zeros, label='Y', color='#44FF44')
        self.line_az, = self.ax_accel.plot(xs, zeros, label='Z', color='#4444FF')
        self.ax_accel.legend(loc='upper right', fontsize='small')

        # Bar chart pour flex
        fingers = ['Pouce', 'Index', 'Majeur', 'Annul.', 'Auric.']
        self.bars = self.ax_flex.bar(fingers, [0] * 5, color='#00FFAA')
        self.ax_flex.set_ylim(0, 4096)  # ESP32 ADC range

        self.fig.tight_layout()

        # Canvas Tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.draw()

        # Désactiver la navigation par défaut de matplotlib pour éviter les conflits
        canvas_widget = self.canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True)

        # Configurer pour éviter les blocages de la souris
        try:
            from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk
            # Pas de toolbar pour éviter les interférences
        except:
            pass

    def _setup_ax(self, ax, title, ylabel):
        ax.set_title(title, color='white', fontsize=10)
        ax.set_facecolor('#0d0d1a')
        ax.grid(True, color='#333333', linestyle='--')
        ax.tick_params(colors='#AAAAAA', labelsize=8)
        ax.yaxis.label.set_color('#AAAAAA')
        ax.set_ylabel(ylabel)
        if hasattr(ax, 'set_xlim'):
            ax.set_xlim(0, self.history_len)

    def update_data(self, data: dict):
        """Met à jour les données locales depuis le flux principal"""
        if not self.is_running:
            return

        hand_data = data.get(self.current_hand, {})
        if not hand_data:
            return

        gyro = hand_data.get('gyro', {})
        accel = hand_data.get('accel', {})
        flex = hand_data.get('flex_sensors', [])

        # Gyro
        self.gyro_x.append(gyro.get('x', 0))
        self.gyro_y.append(gyro.get('y', 0))
        self.gyro_z.append(gyro.get('z', 0))

        # Accel
        self.accel_x.append(accel.get('x', 0))
        self.accel_y.append(accel.get('y', 0))
        self.accel_z.append(accel.get('z', 0))

        # Flex
        if len(flex) >= 5:
            self.flex_vals = flex[:5]

    def _animate(self):
        """Boucle de rafraîchissement graphique"""
        if not self.is_running:
            return

        try:
            # Update Gyro Data seulement si des données existent
            if len(self.gyro_x) > 0:
                def get_padded(d):
                    l = list(d)
                    if len(l) < self.history_len:
                        return [0] * (self.history_len - len(l)) + l
                    return l

                # Mise à jour des données sans bloquer
                self.line_gx.set_ydata(get_padded(self.gyro_x))
                self.line_gy.set_ydata(get_padded(self.gyro_y))
                self.line_gz.set_ydata(get_padded(self.gyro_z))

                # Rescale axes dynamique (optimisé)
                self.ax_gyro.relim()
                self.ax_gyro.autoscale_view(scalex=False, scaley=True)

                self.line_ax.set_ydata(get_padded(self.accel_x))
                self.line_ay.set_ydata(get_padded(self.accel_y))
                self.line_az.set_ydata(get_padded(self.accel_z))

                self.ax_accel.relim()
                self.ax_accel.autoscale_view(scalex=False, scaley=True)

                # Flex bars (optimisé)
                for rect, h in zip(self.bars, self.flex_vals):
                    rect.set_height(h)

            # Utiliser draw_idle au lieu de draw pour éviter les blocages
            self.canvas.draw_idle()
            # Forcer le rafraîchissement sans bloquer
            self.canvas.flush_events()

        except Exception as e:
            print(f"Erreur anim: {e}")

        # Rafraîchissement à 15 FPS pour réduire la charge (au lieu de 20 FPS)
        self.after(66, self._animate)

    def _toggle_hand(self):
        val = self.hand_switch.get()
        # CustomTkinter Switch return values can be tricky if using string vars.
        # Assuming onvalue works. But standard Switch returns 1/0 usually unless variable used.
        # Let's check manually
        # Switch CTk: if connected to StringVar uses onvalue/offvalue. 
        # Here I didn't verify if I should use variable. Let's fix logic.

        if self.current_hand == "right_hand":
            self.current_hand = "left_hand"
            self.hand_switch.configure(text="Main Gauche")
        else:
            self.current_hand = "right_hand"
            self.hand_switch.configure(text="Main Droite")

        # Reset buffers
        self.gyro_x.clear()
        self.gyro_y.clear()
        self.gyro_z.clear()
        self.accel_x.clear()
        self.accel_y.clear()
        self.accel_z.clear()

    def _on_close(self):
        self.is_running = False
        self.destroy()
