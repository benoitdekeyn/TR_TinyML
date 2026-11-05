import re
from html import escape

from vpython import canvas, wtext

from core_3D import BG_COLOR, CONTROL_HEIGHT, FONT_SIZE, WINDOW_WIDTH, IMUVisualizer3D
from core_filtre import OrientationFilter
from core_graphe import RealtimeGraphs
from core_html import fill, read_asset, render_template

PAGE_WIDTH = WINDOW_WIDTH - 30
EMPTY = "--"


def _compact(html):
    return re.sub(r">\s+<", "><", html).strip()


class FeaturePanel:
    """Ligne de valeurs des features : un seul wtext rendu depuis interface_web/feature_panel.html."""

    def __init__(self):
        self._template = read_asset("feature_panel.html")
        self._displayed = None
        self.widget = None

    def slot(self):
        def create(position):
            self.widget = wtext(text="", pos=position)
            self._render(self._values(0.0, None))
        return create

    @staticmethod
    def _values(period_ms, sample):
        if sample is None:
            movement, state = EMPTY, "imu-unknown"
        elif sample.movement:
            movement, state = "Détecté", "imu-moving"
        else:
            movement, state = "Non détecté", "imu-still"
        return {
            "period": f"{period_ms:.0f} ms" if period_ms > 0 else "-- ms",
            "mean": EMPTY if sample is None else f"{sample.mean:.3f}",
            "standard_deviation": EMPTY if sample is None else f"{sample.standard_deviation:.3f}",
            "variance": EMPTY if sample is None else f"{sample.variance:.3f}",
            "rms": EMPTY if sample is None else f"{sample.rms:.3f}",
            "movement": movement,
            "movement_state": state,
        }

    def _render(self, values):
        html = _compact(fill(self._template, {k: escape(v) for k, v in values.items()}))
        if html != self._displayed:
            self.widget.text = html
            self._displayed = html

    def update(self, period_ms, sample):
        self._render(self._values(period_ms, sample))

    def reset(self):
        self.update(0.0, None)


class CoreInterface:
    """Assemble l'interface VPython et relie ses vues aux valeurs des processeurs."""

    def __init__(self, on_connect, on_disconnect, default_com=6):
        self.filter = OrientationFilter()
        # Canevas de 1 px créé en premier : son titre porte tout le haut de page (top_panel.html).
        top = canvas(width=PAGE_WIDTH, height=1, background=BG_COLOR)
        self.graphs = RealtimeGraphs()
        self.feature_panel = FeaturePanel()
        # La scène est créée en dernier pour rester le canevas courant des objets 3D.
        self.visualizer = IMUVisualizer3D(
            on_connect=on_connect,
            on_disconnect=on_disconnect,
            default_com=default_com,
        )
        stylesheet = (
            read_asset("styles.css")
            .replace("{{FONT_SIZE}}", str(FONT_SIZE))
            .replace("{{CONTROL_HEIGHT}}", str(CONTROL_HEIGHT))
            .replace("{{FONT_PADDING}}", str(FONT_SIZE // 2))
            .replace("{{PAGE_WIDTH}}", str(PAGE_WIDTH))
        )
        top.append_to_title(f"<style>{stylesheet}</style>")
        slots = {**self.visualizer.slots(), **self.graphs.slots(), "features": self.feature_panel.slot()}
        render_template(top, "top_panel.html", slots)

    def clear(self):
        self.filter = OrientationFilter()
        self.graphs.clear()
        self.feature_panel.reset()

    def on_sample(self, timestamp, accel, gyro):
        self.filter.update(accel, gyro)
        self.graphs.add_sample(timestamp, accel, gyro)

    def refresh(self, imu_frequency, feature_period_ms, fps, feature_sample):
        self.visualizer.update_pose(self.filter.pose())
        self.graphs.refresh()
        self.visualizer.update_frequency(imu_frequency, fps)
        self.feature_panel.update(feature_period_ms, feature_sample)