import math
import os
import queue
import threading
from dataclasses import dataclass

from core_CSV import CSVRecorder, DEFAULT_OUTPUT_DIR, TIMESTAMP_RE

DEFAULT_YEAR = "2000"
FEATURE_CSV_HEADER = ("timestamp", "moyenne", "ecart-type", "variance", "RMS", "movement")


@dataclass(frozen=True)
class FeatureSample:
    timestamp: str
    mean: float
    standard_deviation: float
    variance: float
    rms: float
    movement: bool


class FeatureProcessor:
    """Décode les trames features, met à jour leur dernière valeur et les enregistre."""

    def __init__(self, output_dir=DEFAULT_OUTPUT_DIR, is_recording=lambda: True, send_date=None):
        self.is_recording = is_recording
        self.send_date = send_date
        self.recorder = CSVRecorder(
            os.path.join(output_dir, "features"),
            min_rows=1,
            header=FEATURE_CSV_HEADER,
        )
        self._frames = queue.SimpleQueue()
        self._stop_frame = object()
        self._pause_recording_frame = object()
        self._thread = None
        self._lock = threading.Lock()
        self._latest = None
        self._sequence = 0
        self.invalid_frames = 0

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._process_frames, daemon=True)
        self._thread.start()

    def submit_frame(self, frame):
        self._frames.put((bytes(frame), self.is_recording()))

    def pause_recording(self):
        self._frames.put(self._pause_recording_frame)

    @staticmethod
    def parse_frame(frame):
        fields = frame.decode("ascii").strip().split(",")
        if len(fields) != 6 or not TIMESTAMP_RE.fullmatch(fields[0]):
            return None
        if fields[-1].strip() not in ("0", "1"):
            return None
        try:
            values = tuple(float(value) for value in fields[1:5])
        except ValueError:
            return None
        if not all(math.isfinite(value) for value in values):
            return None
        return FeatureSample(fields[0], *values, fields[-1].strip() == "1")

    def snapshot(self):
        with self._lock:
            return self._sequence, self._latest

    def _process_frames(self):
        while True:
            frame = self._frames.get()
            if frame is self._stop_frame:
                return
            if frame is self._pause_recording_frame:
                self.recorder.close()
                continue
            frame, should_record = frame
            try:
                sample = self.parse_frame(frame)
            except UnicodeDecodeError:
                sample = None
            if sample is None:
                self.invalid_frames += 1
                continue

            if sample.timestamp.startswith(DEFAULT_YEAR):
                if self.send_date is not None:
                    self.send_date()
            elif should_record and self.is_recording():
                self.recorder.write(
                    sample.timestamp,
                    (sample.mean, sample.standard_deviation, sample.variance, sample.rms,
                     int(sample.movement)),
                )
            else:
                self.recorder.close()

            with self._lock:
                self._latest = sample
                self._sequence += 1

    def stop(self):
        if self._thread is not None and self._thread.is_alive():
            self._frames.put(self._stop_frame)
            self._thread.join()
        self.recorder.close()
