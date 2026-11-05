import serial
import threading
import time
from datetime import datetime

DEFAULT_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
DATE_RESEND_DELAY = 1.0
FREQ_PERIOD_S = 1.0
STALE_FACTOR = 2.5
MAX_CONSECUTIVE_ERRORS = 20
ERROR_RETRY_DELAY = 0.05


class RateMeter:
    """Compte les événements et publie leur fréquence à intervalles réguliers."""

    def __init__(self, period_s=FREQ_PERIOD_S):
        self.period_s = period_s
        self._lock = threading.Lock()
        self._count = 0
        self._last_tick = 0.0
        self._rate = 0.0
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        with self._lock:
            self._count = 0
            self._last_tick = 0.0
            self._rate = 0.0
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
                self._rate = count / (now - period_start)
            period_start = now
            deadline += self.period_s
            if deadline <= now:
                deadline = now + self.period_s

    def stable_rate(self):
        with self._lock:
            if time.perf_counter() - self._last_tick > STALE_FACTOR * self.period_s:
                return 0.0
            return self._rate

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join()


class SerialReceiver:
    """Lit les trames série, les compte et les transmet brutes au processeur IMU."""

    def __init__(self, port, on_frame, baudrate=DEFAULT_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.on_frame = on_frame
        self.serial_conn = None
        self.is_running = False
        self.thread = None
        self.freq_meter = RateMeter()
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
        self.freq_meter.start()
        self.send_date()
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print(f"[*] Connecté au port {self.port}")
        return True

    def get_frequency(self):
        return self.freq_meter.stable_rate()

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
                self.freq_meter.tick()
                self.on_frame(bytes(ligne))

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
        self.freq_meter.stop()
