# 📡 Protocole de Communication ESP32

## Vue d'ensemble

L'application LSF-Cam communique avec les gants ESP32 via WebSocket en utilisant un **protocole différentiel binaire** pour optimiser la bande passante.

## Architecture

```
┌─────────────┐         WebSocket          ┌──────────────────┐
│   ESP32     │◄──────────────────────────►│   Application    │
│  (Maître)   │    Paquets binaires        │    Python        │
│             │                             │                  │
│   ESP32     │                             │  - Décodeur      │
│  (Esclave)  │                             │  - Visualisation │
└─────────────┘                             │  - Prédiction    │
                                            └──────────────────┘
```

## Format du Paquet Binaire

### Structure

```
┌─────────────┬───────────────┬─────────────────┬─────────────────┐
│ Timestamp   │ Bitmask       │ Deltas ESP1     │ Deltas ESP2     │
│ (4 bytes)   │ (4 bytes)     │ (variable)      │ (variable)      │
└─────────────┴───────────────┴─────────────────┴─────────────────┘
```

### Détails des champs

#### 1. Timestamp (4 bytes, little-endian)
- Horodatage du paquet en millisecondes
- Type: `uint32_t`
- Permet la synchronisation temporelle

#### 2. Bitmask (4 bytes, little-endian)
Indique quels capteurs ont changé depuis le dernier paquet.

**Structure du bitmask (32 bits):**
```
Bits 0-10  : ESP1 (esclave) - Main Gauche
Bits 11-21 : ESP2 (maître)  - Main Droite
Bits 22-31 : Réservés (inutilisés)
```

**Mapping par ESP (11 bits):**
```
Bit 0  : flex[0] - Capteur pouce
Bit 1  : flex[1] - Capteur index
Bit 2  : flex[2] - Capteur majeur
Bit 3  : flex[3] - Capteur annulaire
Bit 4  : flex[4] - Capteur auriculaire
Bit 5  : accelX  - Accélération axe X
Bit 6  : accelY  - Accélération axe Y
Bit 7  : accelZ  - Accélération axe Z
Bit 8  : gyroX   - Rotation axe X
Bit 9  : gyroY   - Rotation axe Y
Bit 10 : gyroZ   - Rotation axe Z
```

#### 3. Deltas (variable)
Pour chaque bit à 1 dans le bitmask, un delta de **2 bytes (int16, little-endian)** suit.

**Premier paquet** : Les deltas sont des **valeurs absolues**
**Paquets suivants** : Les deltas sont des **différences** par rapport à l'état précédent

## Exemple de Décodage

### Paquet hexadécimal
```
01 02 03 04    0F 08 00 00    64 00 C8 00    2C 01
│              │              │              │
Timestamp      Bitmask        Deltas ESP1    Deltas ESP2
```

### Décomposition

**Timestamp:** `0x04030201` = 67305985 ms

**Bitmask:** `0x0000080F`
- ESP1 (bits 0-10): `0x00F` = `0b00000001111`
  - Bits 0-3 à 1 : flex[0], flex[1], flex[2], flex[3] ont changé
- ESP2 (bits 11-21): `0x010` = `0b00000000001` (bit 11 activé)
  - Bit 0 à 1 (11-11): flex[0] a changé

**Deltas ESP1** (4 valeurs × 2 bytes):
- `0x0064` = 100 → flex[0] = 100
- `0x00C8` = 200 → flex[1] = 200
- `0x012C` = 300 → flex[2] = 300
- (...)

## Format JSON Produit

Après décodage, le paquet binaire est converti en JSON :

```json
{
  "timestamp": 67305985,
  "left_hand": {
    "flex_sensors": [100, 200, 300, 400, 500],
    "accel": {"x": 8000, "y": -5000, "z": 16000},
    "gyro": {"x": -70000, "y": 140000, "z": 1500},
    "timestamp": 67305985,
    "initialized": true
  },
  "right_hand": {
    "flex_sensors": [50, 150, 250, 350, 450],
    "accel": {"x": -17000, "y": 4000, "z": -1000},
    "gyro": {"x": 500, "y": -66000, "z": 700},
    "timestamp": 67305985,
    "initialized": true
  },
  "packet_number": 42,
  "bytes_received": 24
}
```

## Utilisation dans le Code

### Python (Application de traduction)

```python
from differential_decoder import DifferentialDecoder

# Créer le décodeur
decoder = DifferentialDecoder()

# Recevoir un paquet binaire via WebSocket
binary_packet = await websocket.recv()

# Décoder
try:
    decoded = decoder.decode(binary_packet)
    data = decoded.to_dict()

    # Utiliser les données
    left_hand = data['left_hand']
    right_hand = data['right_hand']

except DecodeException as e:
    print(f"Erreur de décodage: {e}")
```

### Dart (Application de labélisation)

Le code Dart fourni utilise la même logique et produit le même format JSON.

## Compatibilité

### Rétrocompatibilité
L'application supporte **deux modes** :
1. **Mode binaire** (protocole différentiel) - Recommandé
2. **Mode JSON** (ancien protocole) - Pour compatibilité

Le décodeur détecte automatiquement le type de message :
```python
if isinstance(message, bytes):
    # Mode binaire
    decoded = decoder.decode(message)
else:
    # Mode JSON
    data = json.loads(message)
```

## Avantages du Protocole Différentiel

✅ **Réduction de la bande passante** : ~70% de réduction vs JSON
✅ **Latence minimale** : Transmission uniquement des changements
✅ **Précision** : Valeurs brutes int16 sans perte de précision
✅ **Fiabilité** : Checksum implicite via bitmask

## Mapping des Mains

- **ESP1 (Esclave)** = **Main Gauche** (`left_hand`)
- **ESP2 (Maître)** = **Main Droite** (`right_hand`)

## Valeurs des Capteurs

### Capteurs de Flexion (ADC 12-bit)
- **Plage** : 0 - 4095
- **Type** : uint16
- **Calibration** : Varie selon le capteur et la courbure

### IMU (MPU6050)
**Accéléromètre** :
- **Plage** : ±16g
- **Valeurs brutes** : -32768 à +32767
- **Conversion** : `accel_g = raw / 2048.0`

**Gyroscope** :
- **Plage** : ±2000 deg/s
- **Valeurs brutes** : -32768 à +32767
- **Conversion** : `gyro_deg = raw / 16.4`

## Dépannage

### Erreur "Paquet trop court"
- Vérifiez que le WebSocket est en mode binaire
- Minimum 8 bytes (4 timestamp + 4 bitmask)

### Erreur "Paquet incomplet"
- Le nombre de deltas ne correspond pas au bitmask
- Vérifiez la transmission réseau

### Valeurs incohérentes
- Réinitialisez le décodeur : `decoder.reset()`
- Redémarrez la connexion ESP32

## Développement

### Ajouter un nouveau capteur
1. Étendre le bitmask (bits 22-31 disponibles)
2. Modifier `_apply_deltas()` dans les deux implémentations
3. Mettre à jour `ESPState` pour inclure le nouveau capteur

### Debug
Utilisez les méthodes utilitaires :
```python
# Afficher le bitmask en lisible
sensors = DifferentialDecoder.bitmask_to_string(0x00F)
print(sensors)  # "flex0, flex1, flex2, flex3"

# Afficher les bytes en hex
hex_str = DifferentialDecoder.bytes_to_hex(packet_bytes)
print(hex_str)  # "01 02 03 04 0f 08 00 00..."
```

---

**Développé pour LSF-Cam** 🤟
Compatible avec l'application de labélisation Dart/Flutter
