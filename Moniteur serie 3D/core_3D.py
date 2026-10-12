from vpython import canvas, arrow, vector, color

# --- CONSTANTES DE LA FENÊTRE ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1200
BG_COLOR = color.black

# --- CONSTANTES DES AXES DE RÉFÉRENCE ---
AXIS_LENGTH = 2.0
AXIS_WIDTH = 0.02
COLOR_X = color.red
COLOR_Y = color.green
COLOR_Z = color.blue
ORIGIN = vector(0, 0, 0)

# --- CONSTANTES DU VECTEUR ACCÉLÉRATION ---
ACCEL_WIDTH = 0.08
COLOR_ACCEL = color.yellow
DEFAULT_DIR = vector(0, 0, -1)

class IMUVisualizer3D:
    def __init__(self, titre="Détection de Chute - Vecteur IMU"):
        # Initialisation de la scène 3D
        self.scene = canvas(title=titre, width=WINDOW_WIDTH, height=WINDOW_HEIGHT, background=BG_COLOR)
        self.scene.autoscale = False
        
        # Création des axes de référence (repère fixe)
        arrow(pos=ORIGIN, axis=vector(AXIS_LENGTH, 0, 0), color=COLOR_X, shaftwidth=AXIS_WIDTH)
        arrow(pos=ORIGIN, axis=vector(0, AXIS_LENGTH, 0), color=COLOR_Y, shaftwidth=AXIS_WIDTH)
        arrow(pos=ORIGIN, axis=vector(0, 0, AXIS_LENGTH), color=COLOR_Z, shaftwidth=AXIS_WIDTH)
        
        # Le vecteur d'accélération qui sera mis à jour
        self.accel_arrow = arrow(pos=ORIGIN, axis=DEFAULT_DIR, color=COLOR_ACCEL, shaftwidth=ACCEL_WIDTH)

    def update_vector(self, x, y, z):
        # Mise à jour de la direction et de la norme du vecteur
        self.accel_arrow.axis = vector(x, y, z)