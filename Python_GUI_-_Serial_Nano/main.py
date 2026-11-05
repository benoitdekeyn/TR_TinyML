from vpython import rate
from core_IMU import IMUProcessor
from core_Serial import RateMeter, SerialReceiver
from core_filtre import OrientationFilter
from core_graphe import RealtimeGraphs
# --- CONSTANTES GLOBALES ---
DEFAULT_COM_NUMBER = 6
WINDOW_TITLE = "Lecture IMU Nano 33 BLE"
FPS_LIMIT = 60 

from core_3D import IMUVisualizer3D

def main():
    state = {"lecteur": None, "processeur": None}
    filtre = OrientationFilter()

    graphes = RealtimeGraphs(WINDOW_TITLE)  # Créés avant la 3D : titre + durée, puis graphes, au-dessus de la 3D

    def on_sample(timestamp, accel, gyro):
        filtre.update(accel, gyro)
        graphes.add_sample(timestamp, accel, gyro)

    def connecter(port):
        graphes.clear()
        processeur = IMUProcessor(on_sample=on_sample, is_recording=lambda: not graphes.paused)
        lecteur = SerialReceiver(port=port, on_frame=processeur.submit_frame)
        processeur.send_date = lecteur.send_date
        processeur.start()
        if lecteur.start():
            state["lecteur"] = lecteur
            state["processeur"] = processeur
            return True
        processeur.stop()
        return False

    def deconnecter():
        lecteur, state["lecteur"] = state["lecteur"], None
        processeur, state["processeur"] = state["processeur"], None
        if lecteur is not None:
            lecteur.stop()
        if processeur is not None:
            processeur.stop()

    afficheur = IMUVisualizer3D(
        on_connect=connecter, on_disconnect=deconnecter, default_com=DEFAULT_COM_NUMBER
    )
    print(f"[*] Interface lancée à {FPS_LIMIT} FPS, en attente de connexion...")

    fps_meter = RateMeter()
    fps_meter.start()
    try:
        while True:
            rate(FPS_LIMIT)
            fps_meter.tick()
            lecteur = state["lecteur"]
            if lecteur is None:
                continue
            if lecteur.connection_lost:
                afficheur.disconnect(f"Connexion perdue avec {afficheur.port_name}", False)
                continue
            # Filtre -> 3D : l'afficheur ne reçoit que la pose estimée
            afficheur.update_pose(filtre.pose())
            graphes.refresh()
            afficheur.update_frequency(lecteur.get_frequency(), fps_meter.stable_rate())

    except KeyboardInterrupt:
        print("\n[*] Arrêt demandé...")
        if state["lecteur"] is not None:
            state["lecteur"].stop()
    finally:
        fps_meter.stop()

if __name__ == "__main__":
    main()