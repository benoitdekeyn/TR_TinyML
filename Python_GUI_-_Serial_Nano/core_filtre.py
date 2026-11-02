import threading
import time
from typing import NamedTuple

import imufusion
import numpy as np

# --- CONSTANTES DU FILTRE ---
SAMPLE_RATE_HZ = 50          # Fréquence nominale (sert à l'estimation du biais gyro)
GAIN = 0.5                   # Poids de l'accéléromètre dans la correction (plus haut = converge plus vite, plus bruité)
GYRO_RANGE_DPS = 2000        # Plage du BMI270 : au-delà, le gyro est considéré saturé
ACCEL_REJECTION_DEG = 10.0   # Rejette l'accéléromètre lors des accélérations linéaires
RECOVERY_PERIOD_S = 5        # Délai avant de refaire confiance à l'accéléromètre après un rejet
MAX_DT_S = 0.5               # Au-delà, l'intervalle est ignoré (pause, reconnexion)
ACCEL_SIGN = -1.0            # La carte envoie la gravité (-1 g axe vers le haut), imufusion veut +1 g


class Pose(NamedTuple):
    """Résultat du filtre, consommé par la vue 3D."""
    gravity: tuple   # gravité (vers le bas) dans le repère capteur, même convention que les mesures de la carte
    x_axis: tuple    # axe X du capteur dans le repère monde (Z vers le haut)
    y_axis: tuple    # axe Y du capteur (USB)
    z_axis: tuple    # axe Z du capteur (normale à la carte)
    euler: tuple     # (roulis, tangage, lacet) en degrés


class OrientationFilter:
    """Fusion accéléromètre (g) + gyroscope (°/s) par filtre AHRS (Madgwick amélioré, lib imufusion).
    Sans magnétomètre : roulis et tangage sont absolus (gravité), le lacet est relatif (dérive lente)."""

    def __init__(self, sample_rate=SAMPLE_RATE_HZ):
        self.ahrs = imufusion.Ahrs()
        self.ahrs.set_settings(imufusion.AhrsSettings(
            convention=imufusion.CONVENTION_NWU,
            gain=GAIN,
            gyroscope_range=GYRO_RANGE_DPS,
            acceleration_rejection=ACCEL_REJECTION_DEG,
            magnetic_rejection=0.0,
            rejection_timeout=RECOVERY_PERIOD_S,
            sample_rate=float(sample_rate),
        ))
        self.ahrs.set_sample_period(1.0 / sample_rate)
        self._period = 1.0 / sample_rate
        self._last_t = None
        self._lock = threading.Lock()  # update() tourne dans le thread série, pose() dans le thread 3D

    def update(self, accel, gyro, t=None):
        """Entrée : accel en g, gyro en °/s (repère capteur, repère direct), t en secondes (défaut : horloge locale).
        La carte envoie la gravité (-1 g sur un axe dont la flèche pointe vers le haut) ; imufusion attend
        l'accélération mesurée (+1 g vers le haut), d'où ACCEL_SIGN. Gyro : sens trigonométrique = positif,
        ce qui est la convention d'imufusion."""
        if t is None:
            t = time.perf_counter()
        with self._lock:
            dt = self._period if self._last_t is None else t - self._last_t
            self._last_t = t
            if 0 < dt < MAX_DT_S:
                self.ahrs.set_sample_period(dt)
                self.ahrs.update_no_magnetometer(
                    np.array(gyro, dtype=float), ACCEL_SIGN * np.array(accel, dtype=float)
                )

    def pose(self):
        """Orientation courante, cohérente (un seul instant). Repère monde : Z vers le haut."""
        with self._lock:
            q = self.ahrs.get_quaternion()
            up = self.ahrs.get_gravity()  # imufusion : direction du haut dans le repère capteur
        r = imufusion.quaternion_to_matrix(q)  # colonnes = axes du capteur exprimés dans le monde
        euler = imufusion.quaternion_to_euler(q)
        return Pose(
            gravity=tuple(-float(v) for v in up),  # même convention que la carte : gravité vers le bas
            x_axis=tuple(float(v) for v in r[:, 0]),
            y_axis=tuple(float(v) for v in r[:, 1]),
            z_axis=tuple(float(v) for v in r[:, 2]),
            euler=tuple(float(v) for v in euler),
        )
