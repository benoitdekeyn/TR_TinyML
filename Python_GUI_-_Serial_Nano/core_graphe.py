import math
import threading
import time
from collections import deque

from vpython import graph, gcurve, color, winput, canvas

from core_3D import WINDOW_WIDTH, FONT_SIZE, CONTROL_HEIGHT

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
        self._samples = deque()  # (t, ax, ay, az, gx, gy, gz) avec gyro en rad/s
        self._last_refresh = 0.0
        self.window_s = DEFAULT_WINDOW_S

        self._create_header(titre)
        self._graph_accel, self._curves_accel = self._make_graph(ACCEL_TITLE, ACCEL_CHANNELS)
        self._graph_gyro, self._curves_gyro = self._make_graph(GYRO_TITLE, GYRO_CHANNELS)

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
            f"<span {font}><b>{WINDOW_LABEL}</b></span></div>"
        )
        self.window_input = winput(
            bind=self._on_window_enter, type='numeric', width=int(FONT_SIZE * 3),
            text=f"{self.window_s:g}", pos=header.title_anchor,
        )
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
        return g, curves

    def _on_window_enter(self, w):
        try:
            value = float(w.text.replace(",", "."))
        except ValueError:
            value = self.window_s
        self.window_s = min(MAX_WINDOW_S, max(MIN_WINDOW_S, value))
        w.text = f"{self.window_s:g}"
        self._last_refresh = 0.0

    def add_sample(self, accel_g, gyro_dps):
        """Appelé par le thread série : accel en g, gyro en °/s (converti ici en rad/s)."""
        t = time.perf_counter()
        gyro = [math.radians(v) for v in gyro_dps]
        with self._lock:
            self._samples.append((t, *accel_g, *gyro))
            while self._samples and t - self._samples[0][0] > MAX_WINDOW_S:
                self._samples.popleft()

    def clear(self):
        with self._lock:
            self._samples.clear()

    def refresh(self):
        """Appelé par la boucle principale (thread 3D) ; redessine à REFRESH_HZ."""
        now = time.perf_counter()
        if now - self._last_refresh < 1.0 / REFRESH_HZ:
            return
        self._last_refresh = now
        window = self.window_s
        with self._lock:
            samples = [s for s in self._samples if now - s[0] <= window]

        for g, curves, offset, floor in (
            (self._graph_accel, self._curves_accel, 1, MIN_ACCEL_RANGE_G),
            (self._graph_gyro, self._curves_gyro, 4, MIN_GYRO_RANGE_RADS),
        ):
            peak = max((abs(s[offset + k]) for s in samples for k in range(3)), default=0.0)
            amplitude = max(floor, peak * AMPLITUDE_MARGIN)
            g.xmin, g.xmax = -window, 0
            g.ymin, g.ymax = -amplitude, amplitude
            for k, curve in enumerate(curves):
                curve.data = [[s[0] - now, s[offset + k]] for s in samples]
