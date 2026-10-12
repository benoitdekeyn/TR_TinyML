from vpython import canvas, arrow, vector, color, curve, label, box, menu, cross, mag, acos

# --- CONSTANTES DE FENÊTRE & STYLE CAO ---
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
BG_COLOR = color.white

# --- CONTRÔLES CAO / CAMÉRA ---
USER_ZOOM = True      
USER_SPIN = True      
USER_PAN = True       

# --- CONSTANTES DES AXES DE RÉFÉRENCE DU MONDE ---
AXIS_LENGTH = 2.0
AXIS_WIDTH = 0.02
COLOR_X = color.red
COLOR_Y = color.green
COLOR_Z = color.blue                  
ORIGIN = vector(0, 0, 0)

# --- CONSTANTES DE LA GRILLE (CADRE CAO) ---
GRID_SIZE = 2.0       
GRID_STEP = 0.5       
COLOR_GRID = vector(0.82, 0.82, 0.82) 

# --- CONSTANTES DU VECTEUR D'ACCÉLÉRATION ---
ACCEL_WIDTH = 0.07
COLOR_ACCEL = color.magenta          
DEFAULT_DIR = vector(0, 0, -1)

# --- DIMENSIONS DU MODÈLE CARTE 3D ---
BOARD_WIDTH = 0.8     
BOARD_LENGTH = 2.0    
BOARD_THICK = 0.08    
USB_WIDTH = 0.30      
USB_LENGTH = 0.25     
USB_HEIGHT = 0.12     
MINI_AXIS_LEN = 0.45  # Longueur des flèches du mini-repère


class IMUVisualizer3D:
    def __init__(self, titre="Détection de Chute - Visualiseur 3D"):
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

        self.scene.up = vector(0, 0, 1)
        self.scene.forward = vector(-1, -1, -0.6)

        # Mode actif par défaut : Objet
        self.mode = 'objet'

        # Menu déroulant (Objet placé en premier)
        self.scene.append_to_caption('\n<b>Mode d\'affichage : </b>')
        menu(choices=['Objet (Gravité fixe)', 'Vecteur (IMU fixe)'], bind=self._on_mode_change)
        self.scene.append_to_caption('\n\n')

        self._draw_grid()

        # Repère du monde fixe (masqué par défaut en mode objet)
        self.axe_x = arrow(pos=ORIGIN, axis=vector(AXIS_LENGTH, 0, 0), color=COLOR_X, shaftwidth=AXIS_WIDTH, visible=False)
        self.axe_y = arrow(pos=ORIGIN, axis=vector(0, AXIS_LENGTH, 0), color=COLOR_Y, shaftwidth=AXIS_WIDTH, visible=False)
        self.axe_z = arrow(pos=ORIGIN, axis=vector(0, 0, AXIS_LENGTH), color=COLOR_Z, shaftwidth=AXIS_WIDTH, visible=False)

        self.lbl_x = label(pos=vector(AXIS_LENGTH + 0.1, 0, 0), text='X', box=False, color=COLOR_X, opacity=0, visible=False)
        self.lbl_y = label(pos=vector(0, AXIS_LENGTH + 0.1, 0), text='Y (USB)', box=False, color=COLOR_Y, opacity=0, visible=False)
        self.lbl_z = label(pos=vector(0, 0, AXIS_LENGTH + 0.1), text='Z', box=False, color=COLOR_Z, opacity=0, visible=False)

        # Flèche d'accélération pour le mode Vecteur
        self.accel_arrow = arrow(pos=ORIGIN, axis=DEFAULT_DIR, color=COLOR_ACCEL, shaftwidth=ACCEL_WIDTH, visible=False)

        # --- OBJETS DU MODE OBJET (VISIBLES PAR DÉFAUT) ---
        self.pcb = box(
            pos=ORIGIN,
            length=BOARD_LENGTH,
            height=BOARD_THICK,
            width=BOARD_WIDTH,
            color=vector(0.08, 0.35, 0.18),
            visible=True
        )
        self.usb = box(
            pos=ORIGIN,
            length=USB_LENGTH,
            height=USB_HEIGHT,
            width=USB_WIDTH,
            color=vector(0.65, 0.65, 0.65),
            visible=True
        )

        # Mini-repère attaché sur la face supérieure du PCB
        self.mini_x = arrow(pos=ORIGIN, axis=vector(MINI_AXIS_LEN, 0, 0), color=COLOR_X, shaftwidth=0.015, visible=True)
        self.mini_y = arrow(pos=ORIGIN, axis=vector(0, MINI_AXIS_LEN, 0), color=COLOR_Y, shaftwidth=0.015, visible=True)
        self.mini_z = arrow(pos=ORIGIN, axis=vector(0, 0, MINI_AXIS_LEN), color=COLOR_Z, shaftwidth=0.015, visible=True)

        # Noms des axes du mini-repère
        self.mini_lbl_x = label(pos=ORIGIN, text='X', box=False, height=11, color=COLOR_X, opacity=0, visible=True)
        self.mini_lbl_y = label(pos=ORIGIN, text='Y', box=False, height=11, color=COLOR_Y, opacity=0, visible=True)
        self.mini_lbl_z = label(pos=ORIGIN, text='Z', box=False, height=11, color=COLOR_Z, opacity=0, visible=True)

        # Flèche de gravité fixe pointant vers -Z
        self.gravity_arrow = arrow(pos=ORIGIN, axis=vector(0, 0, -1.5), color=color.cyan, shaftwidth=ACCEL_WIDTH, visible=True)

    def _draw_grid(self):
        val = -GRID_SIZE
        while val <= GRID_SIZE + 1e-5:
            curve(pos=[vector(-GRID_SIZE, val, 0), vector(GRID_SIZE, val, 0)], color=COLOR_GRID, radius=0.003)
            curve(pos=[vector(val, -GRID_SIZE, 0), vector(val, GRID_SIZE, 0)], color=COLOR_GRID, radius=0.003)
            val += GRID_STEP

    def _on_mode_change(self, m):
        if m.selected == 'Objet (Gravité fixe)':
            self.mode = 'objet'
            self.accel_arrow.visible = False
            self.pcb.visible = True
            self.usb.visible = True
            self.mini_x.visible = self.mini_y.visible = self.mini_z.visible = True
            self.mini_lbl_x.visible = self.mini_lbl_y.visible = self.mini_lbl_z.visible = True
            self.gravity_arrow.visible = True
            self.axe_x.visible = self.axe_y.visible = self.axe_z.visible = False
            self.lbl_x.visible = self.lbl_y.visible = self.lbl_z.visible = False
        else:
            self.mode = 'vecteur'
            self.accel_arrow.visible = True
            self.pcb.visible = False
            self.usb.visible = False
            self.mini_x.visible = self.mini_y.visible = self.mini_z.visible = False
            self.mini_lbl_x.visible = self.mini_lbl_y.visible = self.mini_lbl_z.visible = False
            self.gravity_arrow.visible = False
            self.axe_x.visible = self.axe_y.visible = self.axe_z.visible = True
            self.lbl_x.visible = self.lbl_y.visible = self.lbl_z.visible = True

    def update_vector(self, x, y, z):
        v = vector(x, y, z)
        norme = mag(v)
        if norme < 0.01:
            return

        if self.mode == 'vecteur':
            self.accel_arrow.axis = v

        elif self.mode == 'objet':
            v_mesure_norm = v / norme
            v_monde_bas = vector(0, 0, -1)

            axe_rot = cross(v_mesure_norm, v_monde_bas)
            dot_prod = max(-1.0, min(1.0, v_mesure_norm.dot(v_monde_bas)))
            angle_rot = acos(dot_prod)

            x_world = vector(1, 0, 0)
            y_world = vector(0, 1, 0)
            z_world = vector(0, 0, 1)

            if mag(axe_rot) > 0.001:
                x_world = x_world.rotate(angle=angle_rot, axis=axe_rot)
                y_world = y_world.rotate(angle=angle_rot, axis=axe_rot)
                z_world = z_world.rotate(angle=angle_rot, axis=axe_rot)

            # Orientation de la carte
            self.pcb.axis = y_world * BOARD_LENGTH
            self.pcb.up = z_world

            # Positionnement du port USB sur le bord supérieur (+Y)
            offset_y = (BOARD_LENGTH / 2) - (USB_LENGTH / 2)
            offset_z = (BOARD_THICK / 2) + (USB_HEIGHT / 2)
            usb_offset = y_world * offset_y + z_world * offset_z

            self.usb.pos = self.pcb.pos + usb_offset
            self.usb.axis = y_world * USB_LENGTH
            self.usb.up = z_world

            # Origine du mini-repère (centre de la face supérieure du PCB)
            top_center = self.pcb.pos + z_world * (BOARD_THICK / 2)

            self.mini_x.pos = top_center
            self.mini_x.axis = x_world * MINI_AXIS_LEN

            self.mini_y.pos = top_center
            self.mini_y.axis = y_world * MINI_AXIS_LEN

            self.mini_z.pos = top_center
            self.mini_z.axis = z_world * MINI_AXIS_LEN

            # Positionnement des labels au bout de chaque flèche respective
            self.mini_lbl_x.pos = top_center + x_world * (MINI_AXIS_LEN + 0.08)
            self.mini_lbl_y.pos = top_center + y_world * (MINI_AXIS_LEN + 0.08)
            self.mini_lbl_z.pos = top_center + z_world * (MINI_AXIS_LEN + 0.08)