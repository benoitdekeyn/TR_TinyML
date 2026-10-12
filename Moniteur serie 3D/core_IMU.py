import serial
import threading

# --- CONSTANTES DE CONNEXION ---
DEFAULT_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
DEFAULT_DATA = (0.0, 0.0, 1.0) # Vecteur par défaut

class IMUSerialReader:
    def __init__(self, port, baudrate=DEFAULT_BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        self.latest_data = DEFAULT_DATA
        self.thread = None

    def start(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=SERIAL_TIMEOUT)
            self.is_running = True
            self.thread = threading.Thread(target=self._read_loop, daemon=True)
            self.thread.start()
            print(f"[*] Connecté au port {self.port}")
        except Exception as e:
            print(f"[!] Erreur de connexion série : {e}")
            exit(1)

    def _read_loop(self):
        while self.is_running:
            if self.serial_conn.in_waiting > 0:
                try:
                    ligne = self.serial_conn.readline().decode('utf-8').strip()
                    valeurs = ligne.split(',')
                    if len(valeurs) == 3:
                        self.latest_data = tuple(map(float, valeurs))
                except Exception:
                    pass

    def get_data(self):
        return self.latest_data

    def stop(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()