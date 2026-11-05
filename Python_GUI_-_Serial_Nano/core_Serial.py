from collections import deque
import math
import serial
import threading
import time
from datetime import datetime

from core_CSV import TIMESTAMP_RE

DEFAULT_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
DATE_RESEND_DELAY = 1.0
FREQ_PERIOD_S = 1.0
STALE_FACTOR = 2.5
MAX_CONSECUTIVE_ERRORS = 20
ERROR_RETRY_DELAY = 0.05
FRAME_IMU = "imu"
FRAME_FEATURES = "features"
FRAME_OTHER = "other"
FEATURE_PERIOD_WINDOWS = 10
FRAME_PREFIXES = {
    b"IMU": (FRAME_IMU, 7),
    b"FEATURES": (FRAME_FEATURES, 6),
}
PREFIX_SEPARATOR = b">>"


def classify_frame(frame):
    """Retourne (type, contenu CSV sans préfixe) d'une ligne "IMU >> ..." ou "FEATURES >> ...".

    Toute autre ligne, ou une trame au contenu invalide, est de type FRAME_OTHER.
    """
    line = frame.rstrip(b'\r')
    prefix, separator, payload = line.partition(PREFIX_SEPARATOR)
    if not separator:
        return FRAME_OTHER, line
    frame_type, field_count = FRAME_PREFIXES.get(prefix.strip(), (FRAME_OTHER, 0))
    if frame_type == FRAME_OTHER:
        return FRAME_OTHER, line

    payload = payload.strip()
    fields = payload.split(b',')
    if len(fields) != field_count:
        return FRAME_OTHER, line
    try:
        timestamp = fields[0].decode('ascii')
    except UnicodeDecodeError:
        return FRAME_OTHER, line
    if not TIMESTAMP_RE.fullmatch(timestamp):
        return FRAME_OTHER, line

    values = fields[1:-1] if frame_type == FRAME_FEATURES else fields[1:]
    if frame_type == FRAME_FEATURES and fields[-1].strip() not in (b'0', b'1'):
        return FRAME_OTHER, line
    try:
        if not all(math.isfinite(float(value)) for value in values):
            return FRAME_OTHER, line
    except ValueError:
        return FRAME_OTHER, line
    return frame_type, payload


class RateMeter:
    """Moyenne des fréquences (ou de la période) mesurées sur les dernières fenêtres."""

    def __init__(self, period_s=FREQ_PERIOD_S, window_size=1, stale_factor=STALE_FACTOR):
        if period_s <= 0:
            raise ValueError("period_s doit être supérieur à zéro.")
        if window_size <= 0:
            raise ValueError("window_size doit être supérieur à zéro.")
        self.period_s = period_s
        self.window_size = window_size
        self.stale_factor = stale_factor
        self._lock = threading.Lock()
        self._count = 0
        self._last_tick = 0.0
        self._rate = 0.0
        self._rates = deque(maxlen=window_size)
        self._windows = deque(maxlen=window_size)
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        with self._lock:
            self._count = 0
            self._last_tick = 0.0
            self._rate = 0.0
            self._rates.clear()
            self._windows.clear()
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._measure_loop, daemon=True)
        self._thread.start()

    def tick(self, count=1):
        if count <= 0:
            return
        with self._lock:
            self._last_tick = time.perf_counter()
            self._count += count

    def _measure_loop(self):
        period_start = time.perf_counter()
        deadline = period_start + self.period_s
        while not self._stop_event.wait(max(0.0, deadline - time.perf_counter())):
            now = time.perf_counter()
            with self._lock:
                count, self._count = self._count, 0
                self._rates.append(count / (now - period_start))
                self._windows.append((count, now - period_start))
                self._rate = sum(self._rates) / len(self._rates)
            period_start = now
            deadline += self.period_s
            if deadline <= now:
                deadline = now + self.period_s

    def stable_rate(self):
        with self._lock:
            if (self.stale_factor is not None and
                    time.perf_counter() - self._last_tick > self.stale_factor * self.period_s):
                return 0.0
            return self._rate

    def period_ms(self):
        """Période moyenne en ms sur les fenêtres retenues (0.0 sans message)."""
        with self._lock:
            count = sum(window_count for window_count, _ in self._windows)
            if count == 0:
                return 0.0
            return 1000.0 * sum(elapsed for _, elapsed in self._windows) / count

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()


class SerialReceiver:
    """Lit, classe, compte et distribue les trames série complètes."""

    def __init__(self, port, on_imu_frame, on_feature_frame, on_other_frame=None,
                 baudrate=DEFAULT_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.on_imu_frame = on_imu_frame
        self.on_feature_frame = on_feature_frame
        self.on_other_frame = on_other_frame
        self.serial_conn = None
        self.is_running = False
        self.thread = None
        self.imu_freq_meter = RateMeter(window_size=5, stale_factor=None)
        self.feature_freq_meter = RateMeter(window_size=FEATURE_PERIOD_WINDOWS, stale_factor=None)
        self.connection_lost = False
        self.error = ""
        self._last_date_sent = -DATE_RESEND_DELAY

    def start(self):
        """Ouvre le port et lance la réception. Retourne True si la connexion réussit."""
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=SERIAL_TIMEOUT)
        except Exception as e:
            print(f"[!] Erreur de connexion série : {e}")
            return False
        self.is_running = True
        self.imu_freq_meter.start()
        self.feature_freq_meter.start()
        self.send_date()
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[*] Connecté au port {self.port}")
        return True

    def get_frequency(self):
        return self.get_imu_frequency()

    def get_imu_frequency(self):
        return self.imu_freq_meter.stable_rate()

    def get_feature_period_ms(self):
        return self.feature_freq_meter.period_ms()

    def _read_loop(self):
        buffer = bytearray()
        erreurs = 0
        while self.is_running:
            try:
                chunk = self.serial_conn.read(max(1, self.serial_conn.in_waiting))
                erreurs = 0
            except Exception as e:
                if not self.is_running:
                    break
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
                frame_type, payload = classify_frame(bytes(ligne))
                if frame_type == FRAME_IMU:
                    self.imu_freq_meter.tick()
                    self.on_imu_frame(payload)
                elif frame_type == FRAME_FEATURES:
                    self.feature_freq_meter.tick()
                    self.on_feature_frame(payload)
                elif self.on_other_frame is not None:
                    self.on_other_frame(payload)

    def send_date(self):
        now = time.monotonic()
        if now - self._last_date_sent < DATE_RESEND_DELAY:
            return
        self._last_date_sent = now
        try:
            self.serial_conn.write(datetime.now().strftime("date:%Y%m%d%H%M%S\n").encode())
        except Exception:
            pass

    def stop(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        if self.thread is not None:
            self.thread.join()
        self.imu_freq_meter.stop()
        self.feature_freq_meter.stop()
