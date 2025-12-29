"""
DÉCODEUR DIFFÉRENTIEL - PROTOCOLE ESP32
========================================

Format du paquet binaire (WebSocket):
┌─────────────┬───────────────┬─────────────────┬─────────────────┐
│ timestamp   │ bitmask       │ deltas ESP1     │ deltas ESP2     │
│ (4 bytes)   │ (4 bytes)     │ (variable)      │ (variable)      │
└─────────────┴───────────────┴─────────────────┴─────────────────┘

Bitmask (32 bits):
- Bits 0-10  : ESP1 (esclave) - main gauche
- Bits 11-21 : ESP2 (maître) - main droite

Mapping par ESP (11 bits):
- Bits 0-4  : flex[0] à flex[4]
- Bit 5     : accelX
- Bit 6     : accelY
- Bit 7     : accelZ
- Bit 8     : gyroX
- Bit 9     : gyroY
- Bit 10    : gyroZ
"""

import struct
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class Vector3Int:
    """Représente les données d'un accéléromètre ou gyroscope (3 axes)"""
    x: int = 0
    y: int = 0
    z: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {'x': self.x, 'y': self.y, 'z': self.z}

    def __repr__(self) -> str:
        return f"Vector3Int(x={self.x}, y={self.y}, z={self.z})"


@dataclass
class ESPState:
    """État d'un ESP32 (5 capteurs flex + 1 IMU)"""
    flex: List[int] = field(default_factory=lambda: [0] * 5)
    accel: Vector3Int = field(default_factory=Vector3Int)
    gyro: Vector3Int = field(default_factory=Vector3Int)
    timestamp: int = 0
    initialized: bool = False

    def copy(self) -> 'ESPState':
        """Crée une copie profonde de l'état"""
        return ESPState(
            flex=self.flex.copy(),
            accel=Vector3Int(self.accel.x, self.accel.y, self.accel.z),
            gyro=Vector3Int(self.gyro.x, self.gyro.y, self.gyro.z),
            timestamp=self.timestamp,
            initialized=self.initialized
        )

    def to_dict(self) -> Dict:
        return {
            'flex_sensors': self.flex.copy(),
            'accel': self.accel.to_dict(),
            'gyro': self.gyro.to_dict(),
            'timestamp': self.timestamp,
            'initialized': self.initialized
        }

    def __repr__(self) -> str:
        return (f"ESPState(flex={self.flex}, accel={self.accel}, gyro={self.gyro}, "
                f"timestamp={self.timestamp}, initialized={self.initialized})")


@dataclass
class BitmaskInfo:
    """Informations sur le bitmask décodé"""
    combined: int
    esp1: int
    esp2: int

    @property
    def delta_count(self) -> int:
        return self._count_bits(self.combined)

    @property
    def esp1_delta_count(self) -> int:
        return self._count_bits(self.esp1)

    @property
    def esp2_delta_count(self) -> int:
        return self._count_bits(self.esp2)

    @staticmethod
    def _count_bits(n: int) -> int:
        """Compte le nombre de bits à 1"""
        count = 0
        while n:
            count += n & 1
            n >>= 1
        return count

    def to_dict(self) -> Dict:
        return {
            'combined': self.combined,
            'combined_hex': f"0x{self.combined:08x}",
            'esp1': self.esp1,
            'esp1_hex': f"0x{self.esp1:04x}",
            'esp2': self.esp2,
            'esp2_hex': f"0x{self.esp2:04x}",
            'delta_count': self.delta_count
        }

    def __repr__(self) -> str:
        return (f"BitmaskInfo(combined=0x{self.combined:x}, "
                f"esp1=0x{self.esp1:x}, esp2=0x{self.esp2:x})")


@dataclass
class DecodedPacket:
    """Résultat du décodage d'un paquet"""
    timestamp: int
    bitmask: BitmaskInfo
    esp1: ESPState
    esp2: ESPState
    packet_number: int
    bytes_received: int

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'bitmask': self.bitmask.to_dict(),
            'left_hand': self.esp1.to_dict(),
            'right_hand': self.esp2.to_dict(),
            'packet_number': self.packet_number,
            'bytes_received': self.bytes_received
        }

    def __repr__(self) -> str:
        return (f"DecodedPacket(timestamp={self.timestamp}, bitmask={self.bitmask}, "
                f"packet_number={self.packet_number}, bytes_received={self.bytes_received})")


class DecodeException(Exception):
    """Exception levée lors d'erreurs de décodage"""
    pass


class DifferentialDecoder:
    """
    Décodeur de paquets différentiels pour les capteurs ESP32.

    Maintient un état interne et applique les deltas reçus
    pour reconstruire les valeurs complètes des capteurs.

    ESP1 = Main Gauche (esclave)
    ESP2 = Main Droite (maître)
    """

    _ESP2_BIT_OFFSET = 11

    def __init__(self):
        self._esp1 = ESPState()
        self._esp2 = ESPState()
        self._packet_count = 0
        self._last_error: Optional[str] = None

    @property
    def esp1_state(self) -> ESPState:
        """État actuel de l'ESP1 (Main Gauche)"""
        return self._esp1.copy()

    @property
    def esp2_state(self) -> ESPState:
        """État actuel de l'ESP2 (Main Droite)"""
        return self._esp2.copy()

    @property
    def packet_count(self) -> int:
        """Nombre de paquets décodés depuis le dernier reset"""
        return self._packet_count

    @property
    def last_error(self) -> Optional[str]:
        """Dernière erreur de décodage"""
        return self._last_error

    @property
    def esp1_initialized(self) -> bool:
        """L'ESP1 est-il initialisé (a reçu au moins un paquet) ?"""
        return self._esp1.initialized

    @property
    def esp2_initialized(self) -> bool:
        """L'ESP2 est-il initialisé (a reçu au moins un paquet) ?"""
        return self._esp2.initialized

    def decode(self, data: bytes) -> DecodedPacket:
        """
        Décode un paquet binaire et met à jour l'état interne.

        Args:
            data: Paquet binaire reçu via WebSocket (bytes)

        Returns:
            DecodedPacket contenant l'état complet reconstruit

        Raises:
            DecodeException: Si le paquet est invalide
        """
        self._last_error = None

        if len(data) < 8:
            self._last_error = f"Paquet trop court: {len(data)} bytes (minimum 8)"
            raise DecodeException(self._last_error)

        offset = 0

        # Timestamp (4 bytes, little-endian unsigned)
        timestamp = struct.unpack_from('<I', data, offset)[0]
        offset += 4

        # Bitmask combiné (4 bytes, little-endian unsigned)
        bitmask = struct.unpack_from('<I', data, offset)[0]
        offset += 4

        # Extraire les bitmasks individuels
        bitmask_esp1 = bitmask & 0x7FF  # Bits 0-10
        bitmask_esp2 = (bitmask >> self._ESP2_BIT_OFFSET) & 0x7FF  # Bits 11-21

        # Compter les deltas attendus
        expected_deltas = self._count_bits(bitmask)
        expected_bytes = 8 + (expected_deltas * 2)

        if len(data) < expected_bytes:
            self._last_error = (f"Paquet incomplet: {len(data)} bytes reçus, "
                              f"{expected_bytes} attendus ({expected_deltas} deltas)")
            raise DecodeException(self._last_error)

        # Appliquer les deltas ESP1 puis ESP2 (ordre important!)
        offset = self._apply_deltas(data, offset, bitmask_esp1, self._esp1, timestamp)
        offset = self._apply_deltas(data, offset, bitmask_esp2, self._esp2, timestamp)

        self._packet_count += 1

        return DecodedPacket(
            timestamp=timestamp,
            bitmask=BitmaskInfo(
                combined=bitmask,
                esp1=bitmask_esp1,
                esp2=bitmask_esp2
            ),
            esp1=self._esp1.copy(),
            esp2=self._esp2.copy(),
            packet_number=self._packet_count,
            bytes_received=len(data)
        )

    def _apply_deltas(
        self,
        data: bytes,
        offset: int,
        bitmask: int,
        esp: ESPState,
        timestamp: int
    ) -> int:
        """Applique les deltas à un état ESP"""
        esp.timestamp = timestamp
        is_first = not esp.initialized

        if bitmask != 0:
            esp.initialized = True

        # Flex sensors (bits 0-4)
        for i in range(5):
            if bitmask & (1 << i):
                delta = struct.unpack_from('<h', data, offset)[0]  # int16 little-endian
                offset += 2
                if is_first:
                    esp.flex[i] = delta  # Valeur absolue
                else:
                    esp.flex[i] += delta  # Delta

        # Accéléromètre (bits 5-7)
        if bitmask & (1 << 5):
            delta = struct.unpack_from('<h', data, offset)[0]
            offset += 2
            esp.accel.x = delta if is_first else esp.accel.x + delta

        if bitmask & (1 << 6):
            delta = struct.unpack_from('<h', data, offset)[0]
            offset += 2
            esp.accel.y = delta if is_first else esp.accel.y + delta

        if bitmask & (1 << 7):
            delta = struct.unpack_from('<h', data, offset)[0]
            offset += 2
            esp.accel.z = delta if is_first else esp.accel.z + delta

        # Gyroscope (bits 8-10)
        if bitmask & (1 << 8):
            delta = struct.unpack_from('<h', data, offset)[0]
            offset += 2
            esp.gyro.x = delta if is_first else esp.gyro.x + delta

        if bitmask & (1 << 9):
            delta = struct.unpack_from('<h', data, offset)[0]
            offset += 2
            esp.gyro.y = delta if is_first else esp.gyro.y + delta

        if bitmask & (1 << 10):
            delta = struct.unpack_from('<h', data, offset)[0]
            offset += 2
            esp.gyro.z = delta if is_first else esp.gyro.z + delta

        return offset

    @staticmethod
    def _count_bits(n: int) -> int:
        """Compte le nombre de bits à 1 dans un entier"""
        count = 0
        while n:
            count += n & 1
            n >>= 1
        return count

    def reset(self):
        """Réinitialise l'état du décodeur"""
        self._esp1 = ESPState()
        self._esp2 = ESPState()
        self._packet_count = 0
        self._last_error = None

    def get_state(self) -> Dict:
        """Retourne l'état actuel complet"""
        return {
            'left_hand': self._esp1.to_dict(),
            'right_hand': self._esp2.to_dict(),
            'packet_count': self._packet_count,
            'last_error': self._last_error
        }

    @staticmethod
    def bitmask_to_string(bitmask: int) -> str:
        """Convertit un bitmask en représentation lisible"""
        names = [
            'flex0', 'flex1', 'flex2', 'flex3', 'flex4',
            'accelX', 'accelY', 'accelZ',
            'gyroX', 'gyroY', 'gyroZ'
        ]

        sensors = [names[i] for i in range(len(names)) if bitmask & (1 << i)]
        return ', '.join(sensors) if sensors else 'aucun'

    @staticmethod
    def bytes_to_hex(data: bytes, max_bytes: int = 32) -> str:
        """Convertit les données brutes en chaîne hexadécimale pour debug"""
        limit = min(len(data), max_bytes)
        hex_str = ' '.join(f'{b:02x}' for b in data[:limit])
        return f"{hex_str}..." if len(data) > max_bytes else hex_str
