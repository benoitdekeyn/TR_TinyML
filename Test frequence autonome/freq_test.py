"""Mesure le débit des trames IMU CSV reçues sur le port série.

Usage : python freq_test.py [COMx] [durée_s]
Les horodatages indiquent le débit reçu par Python, pas l'instant d'émission USB.
"""
import sys
import threading
import time

import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM6"
DUREE_S = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
BAUDRATE = 115200
PERIODE_RAPPORT_S = 1.0
SERIAL_TIMEOUT_S = 0.05
MAX_FRAME_SIZE = 512


def main():
    if DUREE_S <= 0:
        raise ValueError("La durée doit être supérieure à zéro.")

    ser = serial.Serial(PORT, BAUDRATE, timeout=SERIAL_TIMEOUT_S)
    ser.reset_input_buffer()
    print(f"[*] Mesure sur {PORT} pendant {DUREE_S:g} s (Ctrl+C pour arrêter)")

    stop_event = threading.Event()
    stats_lock = threading.Lock()
    stats = {
        "window_frames": 0,
        "total_frames": 0,
        "window_invalid": 0,
        "total_invalid": 0,
    }
    reader_error = []

    def read_serial():
        buffer = bytearray()
        discarding_long_frame = False

        while not stop_event.is_set():
            try:
                chunk = ser.read(max(1, ser.in_waiting))
            except (serial.SerialException, OSError) as exc:
                if not stop_event.is_set():
                    reader_error.append(exc)
                    stop_event.set()
                return

            if not chunk:
                continue

            if discarding_long_frame:
                newline = chunk.find(b'\n')
                if newline < 0:
                    continue
                chunk = chunk[newline + 1:]
                discarding_long_frame = False

            buffer.extend(chunk)
            lines = buffer.split(b'\n')
            buffer = bytearray(lines.pop())

            frames = 0
            invalid = 0
            for line in lines:
                if len(line) <= MAX_FRAME_SIZE and line.startswith(b"IMU") and line.count(b',') == 6:
                    frames += 1
                else:
                    invalid += 1

            if len(buffer) > MAX_FRAME_SIZE:
                buffer.clear()
                discarding_long_frame = True
                invalid += 1

            if frames or invalid:
                with stats_lock:
                    stats["window_frames"] += frames
                    stats["total_frames"] += frames
                    stats["window_invalid"] += invalid
                    stats["total_invalid"] += invalid

    reader = threading.Thread(target=read_serial, name="serial-reader", daemon=True)
    started_ns = time.perf_counter_ns()
    ser.timeout = SERIAL_TIMEOUT_S
    reader.start()
    window_start_ns = started_ns
    next_report_ns = started_ns + int(PERIODE_RAPPORT_S * 1_000_000_000)
    deadline_ns = started_ns + int(DUREE_S * 1_000_000_000)

    try:
        while not stop_event.is_set():
            now_ns = time.perf_counter_ns()
            if now_ns >= deadline_ns:
                break

            wait_ns = min(next_report_ns, deadline_ns) - now_ns
            if stop_event.wait(max(0, wait_ns) / 1_000_000_000):
                break

            now_ns = time.perf_counter_ns()
            if now_ns >= next_report_ns:
                with stats_lock:
                    count = stats["window_frames"]
                    stats["window_frames"] = 0
                    invalid = stats["window_invalid"]
                    stats["window_invalid"] = 0
                elapsed_s = (now_ns - window_start_ns) / 1_000_000_000
                print(f"{count / elapsed_s:6.1f} Hz | {count} trames"
                      f" | lignes invalides {invalid}")
                window_start_ns = now_ns
                next_report_ns += int(PERIODE_RAPPORT_S * 1_000_000_000)
                if next_report_ns <= now_ns:
                    next_report_ns = now_ns + int(PERIODE_RAPPORT_S * 1_000_000_000)
    except KeyboardInterrupt:
        print("\n[*] Arrêt demandé...")
    finally:
        stop_event.set()
        reader.join()
        ser.close()

    if reader_error:
        raise reader_error[0]

    total_s = (time.perf_counter_ns() - started_ns) / 1_000_000_000
    with stats_lock:
        total_frames = stats["total_frames"]
        invalid_lines = stats["total_invalid"]
    print(f"[*] Moyenne globale : {total_frames / total_s:.2f} Hz "
          f"({total_frames} trames en {total_s:.2f} s, "
          f"{invalid_lines} lignes invalides)")


if __name__ == "__main__":
    main()
