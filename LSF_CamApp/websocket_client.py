"""
Client WebSocket pour la connexion avec l'ESP32
"""

import asyncio
import websockets
import json
import threading
from typing import Callable, Optional
from queue import Queue
from differential_decoder import DifferentialDecoder, DecodeException


class WebSocketClient:
    def __init__(self, url: str):
        self.url = url
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        self.data_queue = Queue()
        self.thread = None
        self.loop = None

        # Décodeur différentiel
        self.decoder = DifferentialDecoder()

        # Callbacks
        self.on_connected: Optional[Callable] = None
        self.on_disconnected: Optional[Callable] = None
        self.on_data: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

    def set_url(self, url: str):
        """Met à jour l'URL WebSocket"""
        self.url = url

    def start(self):
        """Démarre la connexion WebSocket dans un thread séparé"""
        if self.is_running:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Arrête la connexion WebSocket"""
        self.is_running = False
        # Réinitialiser le décodeur
        self.decoder.reset()
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)

    def _run_async_loop(self):
        """Exécute la boucle asyncio dans le thread"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._connect_and_receive())
        except Exception as e:
            if self.on_error:
                self.on_error(str(e))
        finally:
            self.loop.close()

    async def _connect_and_receive(self):
        """Connecte et reçoit les données"""
        retry_delay = 1
        max_retry_delay = 30

        while self.is_running:
            try:
                async with websockets.connect(
                        self.url,
                        ping_interval=20,
                        ping_timeout=10,
                        open_timeout=15,
                        close_timeout=5
                ) as websocket:
                    self.websocket = websocket
                    self.is_connected = True
                    retry_delay = 1

                    if self.on_connected:
                        self.on_connected()

                    async for message in websocket:
                        if not self.is_running:
                            break

                        try:
                            # Vérifier si c'est un message binaire (protocole différentiel)
                            if isinstance(message, bytes):
                                # Décoder le paquet binaire
                                try:
                                    decoded = self.decoder.decode(message)
                                    data = decoded.to_dict()
                                    self.data_queue.put(data)

                                    if self.on_data:
                                        self.on_data(data)
                                except DecodeException as e:
                                    if self.on_error:
                                        self.on_error(f"Erreur décodage: {e}")
                            else:
                                # Message JSON classique (rétrocompatibilité)
                                data = json.loads(message)
                                self.data_queue.put(data)

                                if self.on_data:
                                    self.on_data(data)
                        except json.JSONDecodeError as e:
                            print(f"Erreur JSON: {e}")
                        except Exception as e:
                            print(f"Erreur traitement message: {e}")

            except websockets.exceptions.ConnectionClosed:
                pass
            except asyncio.TimeoutError:
                if self.on_error:
                    self.on_error("Timeout lors de la connexion au gant ESP32. Vérifiez l'adresse IP et que le gant est allumé.")
            except Exception as e:
                if self.on_error:
                    error_msg = str(e)
                    if "timed out" in error_msg.lower():
                        error_msg = "Timeout - Le gant ESP32 ne répond pas. Vérifiez l'IP et la connexion WiFi."
                    self.on_error(error_msg)

            self.is_connected = False
            self.websocket = None

            if self.on_disconnected:
                self.on_disconnected()

            if self.is_running:
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    def get_data(self) -> Optional[dict]:
        """Récupère les données de la queue"""
        if not self.data_queue.empty():
            return self.data_queue.get()
        return None

    def clear_queue(self):
        """Vide la queue de données"""
        while not self.data_queue.empty():
            self.data_queue.get()


class MockWebSocketClient(WebSocketClient):
    """Client mock pour les tests sans ESP32"""

    def __init__(self, url: str):
        super().__init__(url)
        self.mock_running = False

    def start(self):
        """Démarre le mock"""
        import random

        self.is_running = True
        self.mock_running = True

        def generate_mock_data():
            import time

            # Simuler connexion
            time.sleep(0.5)
            self.is_connected = True
            if self.on_connected:
                self.on_connected()

            while self.mock_running:
                # Générer données simulées
                data = {
                    "left_hand": {
                        "gyro": {
                            "x": random.uniform(-70000, 70000),
                            "y": random.uniform(-70000, 140000),
                            "z": random.uniform(-2000, 2000)
                        },
                        "accel": {
                            "x": random.uniform(8000, 16000),
                            "y": random.uniform(-14000, -2000),
                            "z": random.uniform(-12000, 4000)
                        },
                        "flex_sensors": [
                            random.randint(0, 20),
                            random.randint(700, 1500),
                            random.randint(400, 1100),
                            random.randint(1400, 1600),
                            random.randint(0, 10)
                        ]
                    },
                    "right_hand": {
                        "gyro": {
                            "x": random.uniform(-500, 1500),
                            "y": random.uniform(-66000, 2000),
                            "z": random.uniform(-700, 700)
                        },
                        "accel": {
                            "x": random.uniform(-17000, -14000),
                            "y": random.uniform(-6000, 7000),
                            "z": random.uniform(-2000, 4000)
                        },
                        "flex_sensors": [
                            random.randint(0, 100),
                            random.randint(900, 1500),
                            random.randint(1200, 1600),
                            random.randint(900, 1400),
                            random.randint(50, 750)
                        ]
                    }
                }

                self.data_queue.put(data)
                if self.on_data:
                    self.on_data(data)

                time.sleep(0.05)  # 50ms = 20Hz

        self.thread = threading.Thread(target=generate_mock_data, daemon=True)
        self.thread.start()

    def stop(self):
        """Arrête le mock"""
        self.mock_running = False
        self.is_running = False
        self.is_connected = False
        if self.on_disconnected:
            self.on_disconnected()
