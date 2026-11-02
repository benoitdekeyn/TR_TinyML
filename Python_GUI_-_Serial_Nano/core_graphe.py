import math
import os
import threading
from datetime import datetime
import time
from collections import deque

from vpython import graph, gcurve, color, winput, canvas, button, checkbox

from core_3D import WINDOW_WIDTH, FONT_SIZE, CONTROL_HEIGHT
from core_CSV import CSVRecorder, DEFAULT_OUTPUT_DIR

# --- DESIGN DES GRAPHES ---
GRAPH_WIDTH = WINDOW_WIDTH - 30  # Même largeur que le canevas 3D
GRAPH_HEIGHT = 260
GRAPH_BG_COLOR = color.gray(0.1)    # Fond du tracé
GRAPH_TEXT_COLOR = color.white      # Texte, axes, graduations et légende
SHOW_LEGEND = True
ACCEL_TITLE = "Accélération (g)"
GYRO_TITLE = "Gyroscope (rad/s)"
X_AXIS_TITLE = "Temps (s)"
CURVE_LABELS = {"ax": "ax (g)", "ay": "ay (g)", "az": "az (g)",
                "gx": "gx (rad/s)", "gy": "gy (rad/s)", "gz": "gz (rad/s)"}
CURVE_COLORS = {"ax": color.yellow, "ay": color.magenta, "az": color.cyan,
                "gx": color.yellow, "gy": color.magenta, "gz": color.cyan}
ACCEL_CHANNELS = ("ax", "ay", "az")
GYRO_CHANNELS = ("gx", "gy", "gz")

# --- EN-TÊTE (titre + réglage de la durée) ---
HEADER_TITLE_SIZE = FONT_SIZE + 8
HEADER_BG_COLOR = color.gray(0.1)  # Fond du mini-canevas qui porte l'en-tête
WINDOW_LABEL = "Largeur des graphes (s) : "
PLAY_TEXT = "▶ Play"       # Affiché en pause
PAUSE_TEXT = "⏸ Pause"     # Affiché en lecture
REC_START_TEXT = "⏺ Start"
REC_STOP_TEXT = "⏹ Stop"
REC_PAUSE_TEXT = "⏸ Pause"
REC_PLAY_TEXT = "▶ Play"
SYNC_LABEL = "Synchroniser play/pause"
MONITOR_OUTPUT_DIR = os.path.join(DEFAULT_OUTPUT_DIR, "Sessions")  # Dossier des CSV de session
SESSION_PREFIX = "Session_"

# --- ÉCHELLES ---
DEFAULT_WINDOW_S = 5.0           # Largeur de l'échelle de temps par défaut
MIN_WINDOW_S = 0.5
MAX_WINDOW_S = 60.0              # Borne la mémoire conservée et le coût du tracé
AMPLITUDE_MARGIN = 1.1           # Marge au-dessus du pic mesuré
MIN_ACCEL_RANGE_G = 0.1          # Planchers : évitent un zoom infini sur du bruit
MIN_GYRO_RANGE_RADS = 0.1
REFRESH_HZ = 15                  # Cadence de redessin (indépendante de la cadence série)


class RealtimeGraphs:
    """En-tête (titre + durée), puis deux graphes superposés (accélération en g, gyroscope en rad/s),
    axe vertical symétrique zoomé en continu sur l'amplitude mesurée.
    À créer AVANT la vue 3D : l'ordre de création est l'ordre dans la page."""

    def __init__(self, titre=""):
        self._lock = threading.Lock()
        self._samples = deque()  # (t, segment, ax, ay, az, gx, gy, gz) avec gyro en rad/s
        self._last_refresh = 0.0
        self.window_s = DEFAULT_WINDOW_S
        self.paused = False
        self._paused_at = 0.0    # Instant du gel de l'affichage
        self._segment = 0        # Change à chaque reprise : les trous (pauses) ne sont pas reliés
        self._recording = False  # Session CSV en cours
        self._rec_paused = False
        self._monitor_csv = None
        self._session = None

        self._create_header(titre)
        self._graph_accel, self._curves_accel, self._names_accel = self._make_graph(ACCEL_TITLE, ACCEL_CHANNELS)
        self._graph_gyro, self._curves_gyro, self._names_gyro = self._make_graph(GYRO_TITLE, GYRO_CHANNELS)

    def _create_header(self, titre):
        # Un canevas de 1 px sert uniquement d'ancre : son titre accueille le texte et la textbox
        header = canvas(width=GRAPH_WIDTH, height=1, background=HEADER_BG_COLOR)
        font = f'style="font-size: {FONT_SIZE}px; font-family: sans-serif;"'
        # Vpython ajoute les graphes à la fin de la page, après les canevas : le CSS flex (propriété order)
        # remet l'en-tête en premier, puis les graphes, puis le reste (contrôles et vue 3D) dans l'ordre de création.
        header.append_to_title(
            f"<style> input {{ font-size: {FONT_SIZE}px; height: {CONTROL_HEIGHT}px; box-sizing: border-box; }} "
            f"#glowscript {{ display: flex; flex-direction: column; align-items: flex-start; }} "
            f"#glowscript > div:has(.imu-header) {{ order: -2; }} "
            f".glowscript-graph {{ order: -1; }} </style>"
            f"<div class='imu-header'>"
            f"<h2 style='font-size: {HEADER_TITLE_SIZE}px; margin-bottom: 5px; font-family: sans-serif;'>{titre}</h2>"
            f"</div><span {font}><b>{WINDOW_LABEL}</b></span>"
        )
        # Ligne 1 : durée des graphes (champ en fin de ligne, après son libellé)
        self.window_input = winput(
            bind=self._on_window_enter, type='numeric', width=int(FONT_SIZE * 3),
            text=f"{self.window_s:g}", pos=header.title_anchor,
        )
        header.append_to_title("<br>")
        # Ligne 2 : affichage en continu
        header.append_to_title(f"<br><span {font}><b>Lecture IMU : </b></span>")
        self.btn_pause = button(text=PAUSE_TEXT, bind=self._on_pause_click, pos=header.title_anchor)
        header.append_to_title("<br><br>")
        # Ligne 3 : enregistrement
        header.append_to_title(f"<span {font}><b>Enregistrement : </b></span>")
        self.btn_rec = button(text=REC_START_TEXT, bind=self._on_rec_click, pos=header.title_anchor)
        header.append_to_title("&nbsp;&nbsp;&nbsp;")
        self.btn_rec_pause = button(text=REC_PAUSE_TEXT, bind=self._on_rec_pause_click, pos=header.title_anchor)
        self.btn_rec_pause.disabled = True
        header.append_to_title("&nbsp;&nbsp;&nbsp;&nbsp;")
        self.chk_sync = checkbox(text=SYNC_LABEL, bind=lambda c: None, pos=header.title_anchor, checked=False)
        header.append_to_title("<br><br>")

    def _make_graph(self, title, channels):
        g = graph(
            width=GRAPH_WIDTH, height=GRAPH_HEIGHT, title=title,
            xtitle=X_AXIS_TITLE, ytitle=title,
            xmin=-self.window_s, xmax=0, ymin=-1, ymax=1,
            background=GRAPH_BG_COLOR, foreground=GRAPH_TEXT_COLOR,
        )
        curves = [
            gcurve(graph=g, color=CURVE_COLORS[c], label=CURVE_LABELS[c], legend=SHOW_LEGEND)
            for c in channels
        ]
        for curve in curves:
            curve.plot(-self.window_s, 0)  # Un premier point force l'affichage du graphe, donc sa position dans la page
        # Une liste de courbes par canal : une courbe par segment continu, pour ne pas relier les pauses
        return g, [[curve] for curve in curves], channels

    def _on_window_enter(self, w):
        try:
            value = float(w.text.replace(",", "."))
        except ValueError:
            value = self.window_s
        self.window_s = min(MAX_WINDOW_S, max(MIN_WINDOW_S, value))
        w.text = f"{self.window_s:g}"
        self._last_refresh = 0.0

    def _on_pause_click(self, b):
        self.set_paused(not self.paused)

    def _close_part(self):
        # À appeler avec le verrou
        if self._monitor_csv is not None:
            self._monitor_csv.close()
            self._monitor_csv = None

    def _open_part(self):
        # À appeler avec le verrou : nouvelle tranche de la session en cours, nommée d'après
        # le timestamp de sa première ligne (fichier créé à la première mesure écrite)
        self._monitor_csv = CSVRecorder(
            MONITOR_OUTPUT_DIR, name=f"{self._session}_tranche_{{ts}}",
            split_by_minute=False, suffix_format="({})", min_rows=1)

    def set_paused(self, paused):
        """Gèle ou reprend l'affichage (l'enregistrement CSV est indépendant)."""
        with self._lock:
            if paused == self.paused:
                return
            self.paused = paused
            if paused:
                self._paused_at = time.perf_counter()
            else:
                self._segment += 1  # Les points non mesurés pendant la pause restent vides
                # Chaque play de l'affichage ouvre un nouveau fichier de la session en cours
                if self._recording and not self._rec_paused:
                    self._close_part()
                    self._open_part()
        self.btn_pause.text = PLAY_TEXT if paused else PAUSE_TEXT
        self._last_refresh = 0.0

    def _on_rec_click(self, b):
        with self._lock:
            self._close_part()
            self._recording = not self._recording
            self._rec_paused = False
            if self._recording:
                # Nouvelle session, nommée d'après l'heure du démarrage
                self._session = datetime.now().strftime(SESSION_PREFIX + "%Y-%m-%d-%Hh%Mm%Ss")
                self._open_part()
        self.btn_rec.text = REC_STOP_TEXT if self._recording else REC_START_TEXT
        self.btn_rec_pause.text = REC_PAUSE_TEXT
        self.btn_rec_pause.disabled = not self._recording

    def _on_rec_pause_click(self, b):
        with self._lock:
            self._rec_paused = not self._rec_paused
            if self._rec_paused:
                self._close_part()
            else:
                self._open_part()  # Nouvelle partie à chaque reprise
        self.btn_rec_pause.text = REC_PLAY_TEXT if self._rec_paused else REC_PAUSE_TEXT
        if self.chk_sync.checked:
            self.set_paused(self._rec_paused)

    def add_sample(self, timestamp, accel_g, gyro_dps):
        """Appelé par le thread série : accel en g, gyro en °/s (converti ici en rad/s).
        L'affichage gelé ignore la mesure ; le CSV de session l'enregistre si la session n'est pas en pause."""
        t = time.perf_counter()
        gyro = [math.radians(v) for v in gyro_dps]
        with self._lock:
            if not self.paused:
                self._samples.append((t, self._segment, *accel_g, *gyro))
            while self._samples and t - self._samples[0][0] > MAX_WINDOW_S:
                self._samples.popleft()
            # Les mesures datées de l'Arduino non synchronisé (2000) ne sont pas enregistrées
            if self._monitor_csv is not None and not timestamp.startswith("2000"):
                self._monitor_csv.write(timestamp, [*accel_g, *gyro_dps])

    def clear(self):
        """Nouvelle connexion : graphes vidés et affichage démarré. Une session CSV en cours continue."""
        with self._lock:
            self._samples.clear()
            self._segment += 1
        self.set_paused(False)

    def refresh(self):
        """Appelé par la boucle principale (thread 3D) ; redessine à REFRESH_HZ (image figée en pause)."""
        now = time.perf_counter()
        if now - self._last_refresh < 1.0 / REFRESH_HZ:
            return
        self._last_refresh = now
        window = self.window_s
        with self._lock:
            ref = self._paused_at if self.paused else now
            samples = [s for s in self._samples if 0 <= ref - s[0] <= window]

        for g, pools, names, offset, floor in (
            (self._graph_accel, self._curves_accel, self._names_accel, 2, MIN_ACCEL_RANGE_G),
            (self._graph_gyro, self._curves_gyro, self._names_gyro, 5, MIN_GYRO_RANGE_RADS),
        ):
            peak = max((abs(s[offset + k]) for s in samples for k in range(3)), default=0.0)
            amplitude = max(floor, peak * AMPLITUDE_MARGIN)
            g.xmin, g.xmax = -window, 0
            g.ymin, g.ymax = -amplitude, amplitude
            segments = []
            for s in samples:
                if not segments or segments[-1][0] != s[1]:
                    segments.append((s[1], []))
                segments[-1][1].append(s)
            for k, pool in enumerate(pools):
                while len(pool) < len(segments):  # Courbe supplémentaire, sans doublon dans la légende
                    pool.append(gcurve(graph=g, color=CURVE_COLORS[names[k]], legend=False))
                for i, curve in enumerate(pool):
                    if i < len(segments):
                        curve.data = [[s[0] - ref, s[offset + k]] for s in segments[i][1]]
                    elif curve.data:
                        curve.data = []
