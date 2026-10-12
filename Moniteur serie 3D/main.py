from core_IMU import IMUSerialReader
from core_3D import IMUVisualizer3D
from vpython import rate

# --- CONSTANTES GLOBALES ---
PORT_SERIE = 'COM6'
WINDOW_TITLE = "Visualisation Temps Réel Nano 33 BLE"
FPS_LIMIT = 60

def main():
    # 1. Initialisation des modules
    lecteur = IMUSerialReader(port=PORT_SERIE)
    afficheur = IMUVisualizer3D(titre=WINDOW_TITLE)
    
    # 2. Lancement de la lecture des données en arrière-plan
    lecteur.start()
    print(f"[*] Lancement de l'affichage 3D à {FPS_LIMIT} FPS...")
    
    try:
        # 3. Boucle principale
        while True:
            rate(FPS_LIMIT) 
            
            # Récupération et mise à jour
            x, y, z = lecteur.get_data()
            afficheur.update_vector(x, y, z)
            
    except KeyboardInterrupt:
        # Gestion propre de l'arrêt si tu fais Ctrl+C
        print("\n[*] Arrêt du programme...")
        lecteur.stop()

if __name__ == "__main__":
    main()