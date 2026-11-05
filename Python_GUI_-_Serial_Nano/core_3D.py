from vpython import canvas, arrow, vector, color, curve, label, box, menu, winput, button, wtext
import time
from html import escape

from core_html import render_template, widget_slot

FREQ_REFRESH_S = 1.0 # Mise à jour de l'affichage des fréquences, une fois par seconde

# --- CONSTANTES RAPIDES ---
WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 1200
FONT_SIZE = 25
CONTROL_HEIGHT = int(FONT_SIZE * 1.6) # Hauteur commune des champs, boutons et menu
DEFAULT_ZOOM = 2.5
BG_COLOR = color.gray(0.1)
COLOR_X = color.yellow
COLOR_Y = color.magenta
COLOR_Z = color.cyan   
COLOR_GRAVITY = color.white 
COLOR_GRID = vector(0.3, 0.3, 0.3)  

# --- CONTRÔLES CAO / CAMÉRA ---
USER_ZOOM = True      
USER_SPIN = True      
USER_PAN = True      
DEFAULT_ORIENTATION = vector(-1, -1, -0.6)

# --- CONSTANTES DES AXES DE RÉFÉRENCE DU MONDE ---
AXIS_LENGTH = 2.0
AXIS_WIDTH = 0.02              
ORIGIN = vector(0, 0, 0)

# --- CONSTANTES DE LA GRILLE (CADRE CAO) ---
GRID_SIZE = 2.0       
GRID_STEP = 0.5       

# --- CONSTANTES DU VECTEUR D'ACCÉLÉRATION ---
ACCEL_WIDTH = 0.07
DEFAULT_DIR = vector(0, 0, -1)

# --- DIMENSIONS DU MODÈLE CARTE 3D ---
BOARD_WIDTH = 0.8     
BOARD_LENGTH = 2.0    
BOARD_THICK = 0.08    
USB_WIDTH = 0.30      
USB_LENGTH = 0.25     
USB_HEIGHT = 0.12     
MINI_AXIS_LEN = 0.45  
# Le repère capteur suit la sérigraphie (Z vers le haut, carte à plat) : la face haute est donc +Z.
BOARD_TOP_SIGN = 1


class IMUVisualizer3D:
    def __init__(self, on_connect=None, on_disconnect=None, default_com=""):
        # on_connect(nom_port) -> bool : tente la connexion ; on_disconnect() : libère le port
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.connected = False
        self.port_name = ""
        self._last_freq_update = 0.0
        self._last_shown = None

        # Les widgets de connexion vivent dans le canevas du haut (créé par CoreInterface, voir slots()) ;
        # la scène doit rester le dernier canevas créé pour être le canevas courant des objets 3D.
        self.scene = canvas(
            width=WINDOW_WIDTH-30,
            height=WINDOW_HEIGHT-(int)(580*FONT_SIZE/25),
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

        self._default_com = str(default_com)
        render_template(self.scene, "scene_panel.html", {
            "fps": widget_slot(self, "fps_text", lambda pos: wtext(text=self._pill("-- FPS"), pos=pos)),
            "mode_menu": widget_slot(self, "mode_menu", lambda pos: menu(
                choices=['Carte 3D (Gravité fixe)', 'Vecteur Gravité (IMU fixe)'],
                bind=self._on_mode_change, pos=pos)),
        })
        self.mode_menu.disabled = True

        self._create_scene_objects()

    @staticmethod
    def _pill(text):
        return f"<span class='imu-pill'>{escape(text)}</span>"

    def slots(self):
        """Widgets de connexion, à insérer dans le gabarit du haut de page (top_panel.html)."""
        def disabled_button(position):
            self.btn_disconnect = button(text='Déconnecter', bind=self._on_disconnect_click, pos=position)
            self.btn_disconnect.disabled = True

        return {
            "com_input": widget_slot(self, "com_input", lambda pos: winput(
                bind=self._on_com_enter, type='numeric', width=int(FONT_SIZE * 3),
                text=self._default_com, pos=pos)),
            "connect": widget_slot(self, "btn_connect", lambda pos: button(
                text='Tester la connexion', bind=self._on_test_click, pos=pos)),
            "disconnect": disabled_button,
            "status": widget_slot(self, "status", lambda pos: wtext(
                text="<span>En attente de connexion...</span>", pos=pos)),
            "imu_rate": widget_slot(self, "freq_text", lambda pos: wtext(text=self._pill("-- Hz"), pos=pos)),
        }

    def _on_com_enter(self, w):
        self._try_connect()

    def _on_test_click(self, b):
        self._try_connect()

    def _set_status(self, message, ok):
        state = 'imu-status-ok' if ok else 'imu-status-error'
        self.status.text = f"<span class='{state}'>{escape(message)}</span>"

    def _try_connect(self):
        if self.connected:
            return
        numero = self.com_input.text.strip()
        if not numero.isdigit():
            self._set_status("Entrez un numéro de COM valide.", False)
            return
        port = f"COM{numero}"
        self._set_status(f"Test de {port}...", True)
        if self.on_connect is not None and self.on_connect(port):
            self.connected = True
            self.port_name = port
            self._set_status(f"Connecté à {port}", True)
            self.com_input.disabled = True
            self.btn_connect.disabled = True
            self.btn_disconnect.disabled = False
            self.mode_menu.disabled = False
            self.mode_menu.selected = self.mode_menu.choices[0]
            for c in self.grid_curves:
                c.visible = True
            self._apply_mode('objet')
        else:
            self._set_status(f"Échec de connexion à {port}", False)

    def _on_disconnect_click(self, b):
        self.disconnect(f"Déconnecté de {self.port_name}", True)

    def disconnect(self, message, ok):
        if not self.connected:
            return
        self.connected = False
        if self.on_disconnect is not None:
            self.on_disconnect()
        self.com_input.disabled = False
        self.btn_connect.disabled = False
        self.btn_disconnect.disabled = True
        self.mode_menu.disabled = True
        self._hide_scene_objects()
        self.freq_text.text = self._pill("-- Hz")
        self.fps_text.text = self._pill("-- FPS")
        self._last_shown = None
        self._set_status(message, ok)

    def _hide_scene_objects(self):
        for obj in (
            *self.grid_curves, self.accel_arrow, self.pcb, self.usb,
            self.mini_x, self.mini_y, self.mini_z,
            self.mini_lbl_x, self.mini_lbl_y, self.mini_lbl_z,
            self.gravity_arrow, self.axe_x, self.axe_y, self.axe_z,
            self.lbl_x, self.lbl_y, self.lbl_z,
        ):
            obj.visible = False

    def _create_scene_objects(self):
        self.grid_curves = []
        self._draw_grid()

        self.axe_x = arrow(pos=ORIGIN, axis=vector(AXIS_LENGTH, 0, 0), color=COLOR_X, shaftwidth=AXIS_WIDTH, visible=False)
        self.axe_y = arrow(pos=ORIGIN, axis=vector(0, AXIS_LENGTH, 0), color=COLOR_Y, shaftwidth=AXIS_WIDTH, visible=False)
        self.axe_z = arrow(pos=ORIGIN, axis=vector(0, 0, AXIS_LENGTH), color=COLOR_Z, shaftwidth=AXIS_WIDTH, visible=False)

        # Taille du texte (height) augmentée à 35
        self.lbl_x = label(pos=vector(AXIS_LENGTH + 0.1, 0, 0), text='X', box=False, height=FONT_SIZE+10, color=COLOR_X, opacity=0, visible=False)
        self.lbl_y = label(pos=vector(0, AXIS_LENGTH + 0.1, 0), text='Y (USB)', box=False, height=FONT_SIZE+10, color=COLOR_Y, opacity=0, visible=False)
        self.lbl_z = label(pos=vector(0, 0, AXIS_LENGTH + 0.1), text='Z', box=False, height=FONT_SIZE+10, color=COLOR_Z, opacity=0, visible=False)

        self.accel_arrow = arrow(pos=ORIGIN, axis=DEFAULT_DIR, color=COLOR_GRAVITY, shaftwidth=ACCEL_WIDTH, visible=False)

        self.pcb = box(
            pos=ORIGIN,
            length=BOARD_LENGTH,
            height=BOARD_THICK,
            width=BOARD_WIDTH,
            color=vector(0.08, 0.35, 0.18),
            visible=False
        )
        self.usb = box(
            pos=ORIGIN,
            length=USB_LENGTH,
            height=USB_HEIGHT,
            width=USB_WIDTH,
            color=vector(0.65, 0.65, 0.65),
            visible=False
        )

        self.mini_x = arrow(pos=ORIGIN, axis=vector(MINI_AXIS_LEN, 0, 0), color=COLOR_X, shaftwidth=0.015, visible=False)
        self.mini_y = arrow(pos=ORIGIN, axis=vector(0, MINI_AXIS_LEN, 0), color=COLOR_Y, shaftwidth=0.015, visible=False)
        self.mini_z = arrow(pos=ORIGIN, axis=vector(0, 0, MINI_AXIS_LEN), color=COLOR_Z, shaftwidth=0.015, visible=False)

        self.mini_lbl_x = label(pos=ORIGIN, text='X', box=False, height=FONT_SIZE+10, color=COLOR_X, opacity=0, visible=False)
        self.mini_lbl_y = label(pos=ORIGIN, text='Y', box=False, height=FONT_SIZE+10, color=COLOR_Y, opacity=0, visible=False)
        self.mini_lbl_z = label(pos=ORIGIN, text='Z', box=False, height=FONT_SIZE+10, color=COLOR_Z, opacity=0, visible=False)

        self.gravity_arrow = arrow(pos=ORIGIN, axis=vector(0, 0, -1.5), color=COLOR_GRAVITY, shaftwidth=ACCEL_WIDTH, visible=False)

    def _draw_grid(self):
        val = -GRID_SIZE
        while val <= GRID_SIZE + 1e-5:
            self.grid_curves.append(curve(pos=[vector(-GRID_SIZE, val, 0), vector(GRID_SIZE, val, 0)], color=COLOR_GRID, radius=0.003, visible=False))
            self.grid_curves.append(curve(pos=[vector(val, -GRID_SIZE, 0), vector(val, GRID_SIZE, 0)], color=COLOR_GRID, radius=0.003, visible=False))
            val += GRID_STEP

    def _on_mode_change(self, m):
        self._apply_mode('objet' if m.selected == 'Carte 3D (Gravité fixe)' else 'vecteur')

    def _apply_mode(self, mode):
        if mode == 'objet':
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

    def update_frequency(self, hz_serie, fps_3d):
        now = time.monotonic()
        if not self.connected or now - self._last_freq_update < FREQ_REFRESH_S:
            return
        self._last_freq_update = now
        hz, fps = round(hz_serie, 1), round(fps_3d)
        if (hz, fps) == self._last_shown:
            return
        self._last_shown = (hz, fps)
        self.freq_text.text = self._pill(f"{hz:.1f} Hz")
        self.fps_text.text = self._pill(f"{fps} FPS")

    def update_pose(self, pose):
        """Affiche une Pose du filtre (core_filtre.Pose) : aucune estimation ici, seulement du rendu."""
        if not self.connected:
            return

        if self.mode == 'vecteur':
            self.accel_arrow.axis = vector(*pose.gravity)

        elif self.mode == 'objet':
            x_world = vector(*pose.x_axis)
            y_world = vector(*pose.y_axis)
            z_world = vector(*pose.z_axis)

            self.pcb.axis = y_world * BOARD_LENGTH
            top_world = z_world * BOARD_TOP_SIGN  # face composants de la carte, vers le haut quand elle est à plat
            self.pcb.up = top_world

            offset_y = (BOARD_LENGTH / 2) - (USB_LENGTH / 2)
            offset_z = (BOARD_THICK / 2) + (USB_HEIGHT / 2)
            usb_offset = y_world * offset_y + top_world * offset_z

            self.usb.pos = self.pcb.pos + usb_offset
            self.usb.axis = y_world * USB_LENGTH
            self.usb.up = top_world

            top_center = self.pcb.pos + top_world * (BOARD_THICK / 2)

            self.mini_x.pos = top_center
            self.mini_x.axis = x_world * MINI_AXIS_LEN

            self.mini_y.pos = top_center
            self.mini_y.axis = y_world * MINI_AXIS_LEN

            self.mini_z.pos = top_center
            self.mini_z.axis = z_world * MINI_AXIS_LEN

            self.mini_lbl_x.pos = top_center + x_world * (MINI_AXIS_LEN + 0.08)
            self.mini_lbl_y.pos = top_center + y_world * (MINI_AXIS_LEN + 0.08)
            self.mini_lbl_z.pos = top_center + z_world * (MINI_AXIS_LEN + 0.08)