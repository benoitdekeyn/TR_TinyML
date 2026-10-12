from vpython import canvas, arrow, vector, color, curve, label, box, menu, cross, mag, acos
# --- CONSTANTES CSS ---
FONT_SIZE = 25

# --- CONSTANTES DE FENÊTRE & STYLE CAO ---
WINDOW_WIDTH = 2000
WINDOW_HEIGHT = 1000
BG_COLOR = color.white

# --- CONTRÔLES CAO / CAMÉRA ---
USER_ZOOM = True      
USER_SPIN = True      
USER_PAN = True      
DEFAULT_ZOOM = 3.5 
DEFAULT_ORIENTATION = vector(-1, -1, -0.6)

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
MINI_AXIS_LEN = 0.45  


class IMUVisualizer3D:
    def __init__(self, titre="Détection de Chute - Visualiseur 3D"):
        # 1. Création du canevas sans titre complexe pour éviter le crash WebGL
        self.scene = canvas(
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            background=BG_COLOR
        )
        self.scene.userzoom = USER_ZOOM
        self.scene.userspin = USER_SPIN
        self.scene.userpan = USER_PAN
        self.scene.autoscale = False

        # --- RECADRAGE DE LA CAMÉRA ---
        self.scene.up = vector(0, 0, 1)
        self.scene.forward = DEFAULT_ORIENTATION
        self.scene.range = DEFAULT_ZOOM

        self.mode = 'objet'

        # 2. Injection sécurisée du HTML et CSS a posteriori
        self.scene.append_to_title(
            f"<style> select {{ font-size: {FONT_SIZE}px; padding: 5px; cursor: pointer; }} </style>"
            f"<h2 style='font-size: {FONT_SIZE + 8}px; margin-bottom: 5px; font-family: sans-serif;'>{titre}</h2>"
            f"<p style='color:#555; font-size: {FONT_SIZE}px; margin: 0 0 15px 0; font-family: sans-serif;'>"
            f"• <b>Orbite :</b> Clic droit + glisser<br>"
            f"• <b>Déplacer (Pan) :</b> Shift + Clic gauche + glisser<br>"
            f"• <b>Zoom :</b> Molette souris</p>"
        )

        self.scene.append_to_title('<span style="font-size: 20px; font-family: sans-serif;"><b>Mode d\'affichage : </b></span>')
        menu(
            choices=['Objet (Gravité fixe)', 'Vecteur (IMU fixe)'],
            bind=self._on_mode_change,
            pos=self.scene.title_anchor
        )
        self.scene.append_to_title('<br><br>')

        self._draw_grid()

        self.axe_x = arrow(pos=ORIGIN, axis=vector(AXIS_LENGTH, 0, 0), color=COLOR_X, shaftwidth=AXIS_WIDTH, visible=False)
        self.axe_y = arrow(pos=ORIGIN, axis=vector(0, AXIS_LENGTH, 0), color=COLOR_Y, shaftwidth=AXIS_WIDTH, visible=False)
        self.axe_z = arrow(pos=ORIGIN, axis=vector(0, 0, AXIS_LENGTH), color=COLOR_Z, shaftwidth=AXIS_WIDTH, visible=False)

        # Taille du texte (height) augmentée à 22
        self.lbl_x = label(pos=vector(AXIS_LENGTH + 0.1, 0, 0), text='X', box=False, height=22, color=COLOR_X, opacity=0, visible=False)
        self.lbl_y = label(pos=vector(0, AXIS_LENGTH + 0.1, 0), text='Y (USB)', box=False, height=22, color=COLOR_Y, opacity=0, visible=False)
        self.lbl_z = label(pos=vector(0, 0, AXIS_LENGTH + 0.1), text='Z', box=False, height=22, color=COLOR_Z, opacity=0, visible=False)

        self.accel_arrow = arrow(pos=ORIGIN, axis=DEFAULT_DIR, color=COLOR_ACCEL, shaftwidth=ACCEL_WIDTH, visible=False)

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

        self.mini_x = arrow(pos=ORIGIN, axis=vector(MINI_AXIS_LEN, 0, 0), color=COLOR_X, shaftwidth=0.015, visible=True)
        self.mini_y = arrow(pos=ORIGIN, axis=vector(0, MINI_AXIS_LEN, 0), color=COLOR_Y, shaftwidth=0.015, visible=True)
        self.mini_z = arrow(pos=ORIGIN, axis=vector(0, 0, MINI_AXIS_LEN), color=COLOR_Z, shaftwidth=0.015, visible=True)

        self.mini_lbl_x = label(pos=ORIGIN, text='X', box=False, height=22, color=COLOR_X, opacity=0, visible=True)
        self.mini_lbl_y = label(pos=ORIGIN, text='Y', box=False, height=22, color=COLOR_Y, opacity=0, visible=True)
        self.mini_lbl_z = label(pos=ORIGIN, text='Z', box=False, height=22, color=COLOR_Z, opacity=0, visible=True)

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

            self.pcb.axis = y_world * BOARD_LENGTH
            self.pcb.up = z_world

            offset_y = (BOARD_LENGTH / 2) - (USB_LENGTH / 2)
            offset_z = (BOARD_THICK / 2) + (USB_HEIGHT / 2)
            usb_offset = y_world * offset_y + z_world * offset_z

            self.usb.pos = self.pcb.pos + usb_offset
            self.usb.axis = y_world * USB_LENGTH
            self.usb.up = z_world

            top_center = self.pcb.pos + z_world * (BOARD_THICK / 2)

            self.mini_x.pos = top_center
            self.mini_x.axis = x_world * MINI_AXIS_LEN

            self.mini_y.pos = top_center
            self.mini_y.axis = y_world * MINI_AXIS_LEN

            self.mini_z.pos = top_center
            self.mini_z.axis = z_world * MINI_AXIS_LEN

            self.mini_lbl_x.pos = top_center + x_world * (MINI_AXIS_LEN + 0.08)
            self.mini_lbl_y.pos = top_center + y_world * (MINI_AXIS_LEN + 0.08)
            self.mini_lbl_z.pos = top_center + z_world * (MINI_AXIS_LEN + 0.08)