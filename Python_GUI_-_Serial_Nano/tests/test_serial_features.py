import csv
import pathlib
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import core_Serial
from core_CSV import CSVRecorder, HEADER
from core_Features import FeatureProcessor
from core_Serial import (
    FRAME_FEATURES,
    FRAME_IMU,
    FRAME_OTHER,
    RateMeter,
    SerialReceiver,
    classify_frame,
)


TIMESTAMP = "2026-11-05 10:00:00.120"
IMU_PAYLOAD = f"{TIMESTAMP},1,2,3,4,5,6".encode()
FEATURE_PAYLOAD = f"{TIMESTAMP},1.2,0.3,0.09,2.4,1".encode()
IMU_FRAME = b"IMU      >> " + IMU_PAYLOAD
FEATURE_FRAME = b"FEATURES >> " + FEATURE_PAYLOAD


class SerialFeaturesTests(unittest.TestCase):
    def test_classifies_imu_features_and_other_frames(self):
        self.assertEqual(classify_frame(IMU_FRAME), (FRAME_IMU, IMU_PAYLOAD))
        self.assertEqual(classify_frame(FEATURE_FRAME + b"\r"), (FRAME_FEATURES, FEATURE_PAYLOAD))
        self.assertEqual(classify_frame(IMU_PAYLOAD)[0], FRAME_OTHER)
        self.assertEqual(classify_frame(b"Erreur : IMU non detectee !")[0], FRAME_OTHER)
        self.assertEqual(classify_frame(b"IMU      >> " + FEATURE_PAYLOAD)[0], FRAME_OTHER)
        self.assertEqual(
            classify_frame(f"FEATURES >> {TIMESTAMP},1.2,NaN,0.09,2.4,1".encode())[0],
            FRAME_OTHER,
        )
        self.assertEqual(
            classify_frame(f"FEATURES >> {TIMESTAMP},1.2,0.3,0.09,2.4,true".encode())[0],
            FRAME_OTHER,
        )

    def test_default_csv_header_and_rows_remain_unchanged(self):
        with tempfile.TemporaryDirectory() as output_dir:
            recorder = CSVRecorder(output_dir, min_rows=1)
            recorder.write(TIMESTAMP, (1, 2, 3, 4, 5, 6))
            recorder.close()

            path = next(pathlib.Path(output_dir).glob("*.csv"))
            with path.open(newline="", encoding="utf-8") as file:
                rows = list(csv.reader(file))
            self.assertEqual(rows[0], HEADER)
            self.assertEqual(rows[1], [TIMESTAMP, "1", "2", "3", "4", "5", "6"])

    def test_receiver_routes_each_valid_type(self):
        class FakeSerial:
            def __init__(self, *args, **kwargs):
                self.data = bytearray(IMU_FRAME + b"\n" + FEATURE_FRAME + b"\n"
                                      + b"Message libre\n")
                self.is_open = True

            @property
            def in_waiting(self):
                return len(self.data)

            def read(self, size):
                if not self.data:
                    time.sleep(0.002)
                    return b""
                chunk = bytes(self.data[:size])
                del self.data[:size]
                return chunk

            def write(self, data):
                return len(data)

            def close(self):
                self.is_open = False

        imu_frames = []
        feature_frames = []
        other_frames = []
        routed = threading.Event()

        def on_other(frame):
            other_frames.append(frame)
            routed.set()

        with patch.object(core_Serial.serial, "Serial", FakeSerial):
            receiver = SerialReceiver(
                "FAKE",
                on_imu_frame=imu_frames.append,
                on_feature_frame=feature_frames.append,
                on_other_frame=on_other,
            )
            self.assertTrue(receiver.start())
            self.assertTrue(routed.wait(1))
            receiver.stop()

        self.assertEqual(imu_frames, [IMU_PAYLOAD])
        self.assertEqual(feature_frames, [FEATURE_PAYLOAD])
        self.assertEqual(other_frames, [b"Message libre"])

    def test_feature_csv_uses_own_header_and_closes_on_pause(self):
        recording = {"enabled": True}
        with tempfile.TemporaryDirectory() as output_dir:
            processor = FeatureProcessor(
                output_dir=output_dir,
                is_recording=lambda: recording["enabled"],
            )
            processor.start()
            processor.submit_frame(FEATURE_PAYLOAD)
            self._wait_until(lambda: processor.snapshot()[0] == 1)

            recording["enabled"] = False
            processor.pause_recording()
            paused_frame = f"2026-11-05 10:00:00.620,1.4,0.5,0.25,2.6,1".encode()
            processor.submit_frame(paused_frame)
            self._wait_until(lambda: processor.recorder._file is None)

            recording["enabled"] = True
            second_frame = f"2026-11-05 10:00:01.120,1.3,0.4,0.16,2.5,0".encode()
            processor.submit_frame(second_frame)
            self._wait_until(lambda: processor.snapshot()[0] == 3)
            processor.stop()

            feature_dir = pathlib.Path(output_dir) / "features"
            files = sorted(feature_dir.glob("*.csv"))
            self.assertEqual([path.name for path in files],
                             ["2026-11-05_10h00(1).csv", "2026-11-05_10h00.csv"])
            data_rows = []
            for path in files:
                with path.open(newline="", encoding="utf-8") as file:
                    rows = list(csv.reader(file))
                self.assertEqual(
                    rows[0],
                    ["timestamp", "moyenne", "ecart-type", "variance", "RMS", "movement"],
                )
                self.assertEqual(len(rows), 2)
                data_rows.extend(rows[1:])
            self.assertNotIn("2026-11-05 10:00:00.620", [row[0] for row in data_rows])

    def test_frequency_meters_count_separate_streams(self):
        imu_meter = RateMeter(period_s=0.05, window_size=5, stale_factor=None)
        feature_meter = RateMeter(period_s=0.05, window_size=5, stale_factor=None)
        imu_meter.start()
        feature_meter.start()
        try:
            imu_meter.tick(10)
            feature_meter.tick(2)
            self._wait_until(lambda: self._window_count(imu_meter) >= 1)
            self._wait_until(lambda: self._window_count(feature_meter) >= 1)
            imu_rate = imu_meter.stable_rate()
            feature_rate = feature_meter.stable_rate()
            self.assertGreater(imu_rate, feature_rate * 3)
            self.assertLess(imu_rate, feature_rate * 7)
        finally:
            imu_meter.stop()
            feature_meter.stop()

    @staticmethod
    def _window_count(meter):
        with meter._lock:
            return len(meter._rates)

    def test_period_is_pooled_over_the_retained_windows(self):
        meter = RateMeter(period_s=1.0, window_size=10, stale_factor=None)
        self.assertEqual(meter.period_ms(), 0.0)
        meter._windows.extend([(1, 1.0), (0, 1.0), (2, 1.0), (1, 1.0)])
        self.assertAlmostEqual(meter.period_ms(), 1000.0)
        meter._windows.extend([(4, 1.0)] * 6)
        self.assertEqual(len(meter._windows), 10)
        self.assertAlmostEqual(meter.period_ms(), 10000.0 / 28)

    @staticmethod
    def _wait_until(predicate, timeout=1.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.002)
        raise AssertionError("Timed out while waiting for the background worker")


if __name__ == "__main__":
    unittest.main()
