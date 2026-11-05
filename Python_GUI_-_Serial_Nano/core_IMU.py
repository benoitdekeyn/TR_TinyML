import queue
import threading

from core_CSV import CSVRecorder, DEFAULT_OUTPUT_DIR

DEFAULT_YEAR = "2000"

class IMUProcessor:
    """Décode les trames brutes et distribue les mesures aux traitements."""

    def __init__(self, output_dir=DEFAULT_OUTPUT_DIR, on_sample=None,
                 is_recording=lambda: True, send_date=None):
        self.on_sample = on_sample
        self.is_recording = is_recording
        self.send_date = send_date
        self.recorder = CSVRecorder(output_dir)
        self._frames = queue.SimpleQueue()
        self._stop_frame = object()
        self._thread = None

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._process_frames, daemon=True)
        self._thread.start()

    def submit_frame(self, frame):
        """Reçoit une trame brute copiée par le lecteur série."""
        self._frames.put(bytes(frame))

    def _process_frames(self):
        while True:
            ligne = self._frames.get()
            if ligne is self._stop_frame:
                return
            try:
                valeurs = ligne.decode('utf-8').strip().split(',')
                if len(valeurs) != 7:
                    continue
                mesures = tuple(map(float, valeurs[1:]))
            except (UnicodeDecodeError, ValueError):
                continue
            if valeurs[0].startswith(DEFAULT_YEAR):
                if self.send_date is not None:
                    self.send_date()
            elif self.is_recording():
                self.recorder.write(valeurs[0], mesures)
            else:
                self.recorder.close()
            if self.on_sample is not None:
                self.on_sample(valeurs[0], mesures[:3], mesures[3:])

    def stop(self):
        if self._thread is not None:
            self._frames.put(self._stop_frame)
            self._thread.join()
        self.recorder.close()
