"""Mesure brute de la fréquence de réception série (sans interface graphique).

Usage : python freq_test.py [COMx] [durée_s]
"""
import sys
import time
import threading
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM6"
DUREE_S = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
BAUDRATE = 115200


def main():
    ser = serial.Serial(PORT, BAUDRATE, timeout=0.1)
    ser.reset_input_buffer()
    print(f"[*] Mesure sur {PORT} pendant {DUREE_S:.0f} s (Ctrl+C pour arrêter)")

    t0 = time.perf_counter()
    count_total = 0
    count_lock = threading.Lock()
    count_window = 0
    stop_reporter = threading.Event()

    def report_frequency():
        nonlocal count_window
        period_start = time.perf_counter()
        deadline = period_start + 1.0
        while not stop_reporter.wait(max(0.0, deadline - time.perf_counter())):
            now = time.perf_counter()
            with count_lock:
                count, count_window = count_window, 0
            print(f"{count / (now - period_start):6.1f} Hz")
            period_start = now
            deadline += 1.0
            if deadline <= now:
                deadline = now + 1.0

    reporter = threading.Thread(target=report_frequency, daemon=True)
    reporter.start()

    try:
        while time.perf_counter() - t0 < DUREE_S:
            if ser.readline():
                with count_lock:
                    count_window += 1
                count_total += 1
    except KeyboardInterrupt:
        pass
    finally:
        stop_reporter.set()
        reporter.join()
        ser.close()

    total = time.perf_counter() - t0
    print(f"[*] Moyenne globale : {count_total / total:.1f} Hz ({count_total} messages en {total:.1f} s)")


if __name__ == "__main__":
    main()
