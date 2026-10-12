from vpython import color, rate, vector

# --- CONSTANTES GLOBALES ---
PORT_SERIE = 'COM6'
WINDOW_TITLE = "Projet TinyML - Détection de Chute"
FPS_LIMIT = 60 

from core_IMU import IMUSerialReader
from core_3D import IMUVisualizer3D

def main():
    lecteur = IMUSerialReader(port=PORT_SERIE)
    afficheur = IMUVisualizer3D(titre=WINDOW_TITLE)

    lecteur.start()
    print(f"[*] Visualisation lancée à {FPS_LIMIT} FPS...")
    
    try:
        while True:
            rate(FPS_LIMIT)
            x, y, z = lecteur.get_data()
            afficheur.update_vector(x, y, z)

    except KeyboardInterrupt:
        print("\n[*] Arrêt demandé...")
        lecteur.stop()

if __name__ == "__main__":
    main()