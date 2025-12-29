import customtkinter as ctk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from history_manager import HistoryManager


class HistoryWindow(ctk.CTkToplevel):
    """Fenêtre de visualisation de l'historique"""

    def __init__(self, parent, history_manager: 'HistoryManager'):
        super().__init__(parent)

        self.history_manager = history_manager

        self.title("Historique des Prédictions")
        self.geometry("600x500")
        self.minsize(500, 400)

        self.transient(parent)
        self.grab_set()

        self._create_ui()
        self._load_data()

    def _create_ui(self):
        """Crée l'interface utilisateur"""

        # === HEADER (Stats) ===
        self.stats_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_frame.pack(fill="x", padx=20, pady=10)

        self.total_label = ctk.CTkLabel(
            self.stats_frame,
            text="Total: 0",
            font=("Arial", 14, "bold")
        )
        self.total_label.pack(side="left", padx=20)

        self.avg_conf_label = ctk.CTkLabel(
            self.stats_frame,
            text="Confiance Moy.: 0%",
            font=("Arial", 14)
        )
        self.avg_conf_label.pack(side="left", padx=20)

        # === LISTE (Scrollable) ===
        list_container = ctk.CTkFrame(self)
        list_container.pack(fill="both", expand=True, padx=20, pady=10)

        # En-têtes
        headers = ctk.CTkFrame(list_container, height=30, fg_color="#333333")
        headers.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(headers, text="Heure", width=100, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(headers, text="Geste", width=150, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(headers, text="Confiance", width=80, anchor="w").pack(side="left", padx=10)

        # Scrollable Frame pour les items
        self.history_list = ctk.CTkScrollableFrame(list_container, fg_color="transparent")
        self.history_list.pack(fill="both", expand=True, padx=5, pady=5)

        # === FOOTER (Actions) ===
        footer = ctk.CTkFrame(self, fg_color="transparent", height=50)
        footer.pack(fill="x", padx=20, pady=20)

        ctk.CTkButton(
            footer,
            text="Effacer tout",
            fg_color="#AA0000",
            hover_color="#CC0000",
            command=self._clear_history,
            width=100
        ).pack(side="left")

        ctk.CTkButton(
            footer,
            text="Fermer",
            fg_color="#555555",
            hover_color="#666666",
            command=self.destroy,
            width=100
        ).pack(side="right")

        ctk.CTkButton(
            footer,
            text="Exporter CSV 📥",
            command=self._export_csv,
            width=120
        ).pack(side="right", padx=10)

    def _load_data(self):
        """Charge et affiche les données"""
        # Nettoyer la liste
        for widget in self.history_list.winfo_children():
            widget.destroy()

        stats = self.history_manager.get_stats()
        entries = self.history_manager.get_entries(limit=50)  # Derniers 50

        # Mettre à jour stats
        self.total_label.configure(text=f"Total: {stats['total_predictions']}")
        self.avg_conf_label.configure(text=f"Confiance Moy.: {stats['avg_confidence'] * 100:.1f}%")

        # Remplir la liste (inversé pour voir les plus récents en haut)
        for entry in reversed(entries):
            row = ctk.CTkFrame(self.history_list, fg_color="transparent")
            row.pack(fill="x", pady=2)

            dt = datetime.fromisoformat(entry['timestamp'])
            time_str = dt.strftime("%H:%M:%S")
            date_str = dt.strftime("%d/%m")

            # Timestamp
            ctk.CTkLabel(
                row,
                text=f"{date_str} {time_str}",
                width=100,
                anchor="w",
                font=("Arial", 12),
                text_color="#AAAAAA"
            ).pack(side="left", padx=10)

            # Geste
            gesture = entry['gesture'].replace("_1", "")
            ctk.CTkLabel(
                row,
                text=gesture,
                width=150,
                anchor="w",
                font=("Arial", 12, "bold"),
                text_color="#FFFFFF"
            ).pack(side="left", padx=10)

            # Confiance
            conf = entry['confidence'] * 100
            color = "#00FF00" if conf > 90 else "#FFD700" if conf > 70 else "#FF8800"

            ctk.CTkLabel(
                row,
                text=f"{conf:.1f}%",
                width=80,
                anchor="w",
                font=("Arial", 12),
                text_color=color
            ).pack(side="left", padx=10)

            # Separator line if needed
            # ctk.CTkFrame(self.history_list, height=1, fg_color="#333333").pack(fill="x")

    def _export_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            title="Exporter l'historique"
        )
        if filename:
            if self.history_manager.export_csv(filename):
                messagebox.showinfo("Succès", "Exportation réussie !")
            else:
                messagebox.showerror("Erreur", "Échec de l'exportation")

    def _clear_history(self):
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment effacer tout l'historique ?"):
            self.history_manager.clear()
            self._load_data()
