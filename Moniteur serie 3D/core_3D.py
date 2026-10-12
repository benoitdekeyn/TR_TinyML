from vpython import canvas, arrow, vector, color, curve, label

# --- CONSTANTES DE FENÊTRE & STYLE CAO ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
BG_COLOR = color.white

# --- CONTRÔLES CAO / CAMÉRA ---
USER_ZOOM = True      # Molette pour zoomer
USER_SPIN = True      # Clic droit pour orbiter/orienter
USER_PAN = True       # Shift + Clic gauche pour translater/déplacer le plan

# --- CONSTANTES DES AXES DE RÉFÉRENCE ---
AXIS_LENGTH = 2.0
AXIS_WIDTH = 0.02
COLOR_X = color.red
COLOR_Y = color.green
COLOR_Z = color.blue
ORIGIN = vector(0, 0, 0)

# --- CONSTANTES DE LA GRILLE (CADRE CAO) ---
GRID_SIZE = 2.0       # Demi-taille du plateau
GRID_STEP = 0.5       # Pas du maillage
COLOR_GRID = vector(0.82, 0.82, 0.82) # Gris clair discret

# --- CONSTANTES DU VECTEUR D'ACCÉLÉRATION ---
ACCEL_WIDTH = 0.07
COLOR_ACCEL = color.magenta
DEFAULT_DIR = vector(0, 0, -1)


class IMUVisualizer3D:
    def __init__(self, titre="Détection de Chute - Visualiseur 3D"):
        # Initialisation du canevas
        self.scene = canvas(
            title=f"<h3>{titre}</h3>"
                  "<p style='color:#555;font-size:12px;margin:0;'>"
                  "• <b>Orbite :</b> Clic droit + glisser<br>"
                  "• <b>Déplacer (Pan) :</b> Shift + Clic gauche + glisser<br>"
                  "• <b>Zoom :</b> Molette souris</p>",
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            background=BG_COLOR
        )
        self.scene.userzoom = USER_ZOOM
        self.scene.userspin = USER_SPIN
        self.scene.userpan = USER_PAN
        self.scene.autoscale = False

        # Configuration de la caméra avec Z vertical et vue isométrique stable
        self.scene.up = vector(0, 0, 1)
        self.scene.forward = vector(-1, -1, -0.6)

        # Dessin de la grille de sol (plan Z = 0)
        self._draw_grid()

        # Repère cartésien fixe (X=Rouge, Y=Vert, Z=Magenta)
        arrow(pos=ORIGIN, axis=vector(AXIS_LENGTH, 0, 0), color=COLOR_X, shaftwidth=AXIS_WIDTH)
        arrow(pos=ORIGIN, axis=vector(0, AXIS_LENGTH, 0), color=COLOR_Y, shaftwidth=AXIS_WIDTH)
        arrow(pos=ORIGIN, axis=vector(0, 0, AXIS_LENGTH), color=COLOR_Z, shaftwidth=AXIS_WIDTH)

        # Libellés discrets des axes
        label(pos=vector(AXIS_LENGTH + 0.1, 0, 0), text='X', box=False, color=COLOR_X, opacity=0)
        label(pos=vector(0, AXIS_LENGTH + 0.1, 0), text='Y', box=False, color=COLOR_Y, opacity=0)
        label(pos=vector(0, 0, AXIS_LENGTH + 0.1), text='Z', box=False, color=COLOR_Z, opacity=0)

        # Vecteur dynamique d'accélération
        self.accel_arrow = arrow(pos=ORIGIN, axis=DEFAULT_DIR, color=COLOR_ACCEL, shaftwidth=ACCEL_WIDTH)

    def _draw_grid(self):
        """Trace une grille plane Z=0 pour donner la perspective CAO."""
        val = -GRID_SIZE
        while val <= GRID_SIZE + 1e-5:
            # Lignes parallèles à X
            curve(pos=[vector(-GRID_SIZE, val, 0), vector(GRID_SIZE, val, 0)], color=COLOR_GRID, radius=0.003)
            # Lignes parallèles à Y
            curve(pos=[vector(val, -GRID_SIZE, 0), vector(val, GRID_SIZE, 0)], color=COLOR_GRID, radius=0.003)
            val += GRID_STEP

    def update_vector(self, x, y, z):
        self.accel_arrow.axis = vector(x, y, z)