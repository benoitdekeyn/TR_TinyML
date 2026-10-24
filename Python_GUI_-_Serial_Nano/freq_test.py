"""Mesure brute de la fréquence de réception série (sans interface graphique).

Usage : python freq_test.py [COMx] [durée_s]
"""
import sys
import time
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "COM6"
DUREE_S = float(sys.argv[2]) if len(sys.argv) > 2 else 10.0
BAUDRATE = 115200


def main():
    ser = serial.Serial(PORT, BAUDRATE, timeout=1)
    ser.reset_input_buffer()
    print(f"[*] Mesure sur {PORT} pendant {DUREE_S:.0f} s (Ctrl+C pour arrêter)")

    t0 = time.perf_counter()
    t_last = t0
    t_report = t0
    count_total = 0
    count_window = 0
    dt_min = float("inf")
    dt_max = 0.0

    try:
        while time.perf_counter() - t0 < DUREE_S:
            if not ser.readline():
                continue
            now = time.perf_counter()
            dt = now - t_last
            t_last = now
            count_total += 1
            count_window += 1
            if count_total > 1:
                dt_min = min(dt_min, dt)
                dt_max = max(dt_max, dt)

            if now - t_report >= 1.0:
                print(f"{count_window / (now - t_report):6.1f} Hz | "
                      f"intervalle min {dt_min * 1000:6.1f} ms, max {dt_max * 1000:6.1f} ms")
                t_report = now
                count_window = 0
                dt_min = float("inf")
                dt_max = 0.0
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()

    total = time.perf_counter() - t0
    print(f"[*] Moyenne globale : {count_total / total:.1f} Hz ({count_total} messages en {total:.1f} s)")


if __name__ == "__main__":
    main()
