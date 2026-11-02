from vpython import rate
from core_IMU import IMUSerialReader, RateMeter
from core_filtre import OrientationFilter
from core_graphe import RealtimeGraphs
# --- CONSTANTES GLOBALES ---
DEFAULT_COM_NUMBER = 6
WINDOW_TITLE = "Lecture IMU Nano 33 BLE"
FPS_LIMIT = 60 

from core_3D import IMUVisualizer3D

def main():
    state = {"lecteur": None}
    filtre = OrientationFilter()

    graphes = RealtimeGraphs(WINDOW_TITLE)  # Créés avant la 3D : titre + durée, puis graphes, au-dessus de la 3D

    def on_sample(accel, gyro):
        filtre.update(accel, gyro)
        graphes.add_sample(accel, gyro)

    def connecter(port):
        # Liaison série -> filtre et graphes : chaque mesure (accel g, gyro °/s)
        graphes.clear()
        lecteur = IMUSerialReader(port=port, on_sample=on_sample)
        if lecteur.start():
            state["lecteur"] = lecteur
            return True
        return False

    def deconnecter():
        lecteur, state["lecteur"] = state["lecteur"], None
        if lecteur is not None:
            lecteur.stop()

    afficheur = IMUVisualizer3D(
        on_connect=connecter, on_disconnect=deconnecter, default_com=DEFAULT_COM_NUMBER
    )
    print(f"[*] Interface lancée à {FPS_LIMIT} FPS, en attente de connexion...")

    try:
        fps_meter = RateMeter()
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

if __name__ == "__main__":
    main()