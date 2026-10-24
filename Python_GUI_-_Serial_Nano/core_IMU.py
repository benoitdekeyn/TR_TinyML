import serial
import sys
import threading
import time

# --- CONSTANTES DE CONNEXION ---
DEFAULT_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
DEFAULT_DATA = (0.0, 0.0, 1.0) # Vecteur par défaut
GIL_SWITCH_INTERVAL = 0.0005   # Le thread de lecture reprend la main en <0,5 ms (5 ms par défaut) : horodatages précis
MAX_CONSECUTIVE_ERRORS = 20    # Erreurs série d'affilée avant de déclarer le port perdu
ERROR_RETRY_DELAY = 0.05

# --- CONSTANTES DE MESURE DE FRÉQUENCE ---
FREQ_PERIOD_S = 1.0 # Période de calcul de la fréquence
STALE_FACTOR = 2.5  # Au-delà de ce nombre de périodes sans événement, la fréquence tombe à 0


class RateMeter:
    """Fréquence moyenne par période, calculée sur les événements eux-mêmes :
    la fenêtre commence et finit sur un événement, donc N événements / N intervalles exacts."""

    def __init__(self, period_s=FREQ_PERIOD_S):
        self.period_s = period_s
        self._lock = threading.Lock()
        self._period_start = None
        self._count = 0
        self._last_tick = 0.0
        self._rate = 0.0

    def tick(self):
        now = time.perf_counter()
        with self._lock:
            self._last_tick = now
            if self._period_start is None:
                self._period_start = now
                return
            self._count += 1
            elapsed = now - self._period_start
            if elapsed >= self.period_s:
                self._rate = self._count / elapsed
                self._period_start = now
                self._count = 0

    def stable_rate(self):
        with self._lock:
            if time.perf_counter() - self._last_tick > STALE_FACTOR * self.period_s:
                return 0.0
            return self._rate

class IMUSerialReader:
    def __init__(self, port, baudrate=DEFAULT_BAUDRATE):
        sys.setswitchinterval(GIL_SWITCH_INTERVAL)
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        self.latest_data = DEFAULT_DATA
        self.thread = None
        self.freq_meter = RateMeter()
        self.connection_lost = False
        self.error = ""

    def start(self):
        """Ouvre le port et lance la lecture. Retourne True si la connexion a réussi."""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=SERIAL_TIMEOUT)
        except Exception as e:
            print(f"[!] Erreur de connexion série : {e}")
            return False
        self.is_running = True
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[*] Connecté au port {self.port}")
        return True

    def get_frequency(self):
        """Fréquence de réception (Hz), moyenne par période de 1 s."""
        return self.freq_meter.stable_rate()

    def _read_loop(self):
        # Lecture par blocs : readline() de pyserial lit octet par octet, soit ~18 reprises du GIL par message,
        # chacune pouvant attendre le thread 3D et retarder l'horodatage.
        buffer = bytearray()
        erreurs = 0
        while self.is_running:
            try:
                chunk = self.serial_conn.read(max(1, self.serial_conn.in_waiting))
                erreurs = 0
            except Exception as e:
                # Erreur passagère tolérée ; si elle persiste, le port est considéré perdu (carte débranchée/reset)
                erreurs += 1
                if erreurs >= MAX_CONSECUTIVE_ERRORS:
                    self.connection_lost = True
                    self.error = str(e)
                    return
                time.sleep(ERROR_RETRY_DELAY)
                continue
            if not chunk:
                continue
            buffer += chunk
            *lignes, buffer = buffer.split(b'\n')
            buffer = bytearray(buffer)
            for ligne in lignes:
                try:
                    valeurs = ligne.decode('utf-8').strip().split(',')
                    if len(valeurs) == 3:
                        self.latest_data = tuple(map(float, valeurs))
                        self.freq_meter.tick()
                except ValueError:
                    pass

    def get_data(self):
        return self.latest_data

    def stop(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()