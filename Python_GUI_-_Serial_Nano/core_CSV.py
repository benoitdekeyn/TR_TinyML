import csv
import os
import re

DEFAULT_OUTPUT_DIR = "recordings"  # Dossier de sortie personnalisable
HEADER = ["timestamp", "ax", "ay", "az", "gx", "gy", "gz"]
MIN_ROWS = 10  # Un fichier de moins de MIN_ROWS mesures est supprimé à la fermeture
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$")


def _minute_name(timestamp):
    """'2026-11-02 16:55:01.123' -> '2026-11-02_16h55' (précision à la minute, valide dans un nom de fichier)."""
    return f"{timestamp[:10]}_{timestamp[11:13]}h{timestamp[14:16]}"


class CSVRecorder:
    """Enregistre les mesures dans des CSV nommés d'après l'horodatage de l'Arduino, à la minute près.
    split_by_minute=True : un nouveau fichier à chaque changement de minute.
    split_by_minute=False : un seul fichier, nommé d'après la première mesure.
    Si le nom existe déjà, un suffixe est ajouté (suffix_format, par défaut '(1)', '(2)'...).
    Un fichier de moins de min_rows mesures est supprimé à la fermeture."""

    def __init__(self, output_dir=DEFAULT_OUTPUT_DIR, prefix="", split_by_minute=True,
                 suffix_format="({})", min_rows=MIN_ROWS, name=None):
        self.name = name  # Nom de fichier imposé (sinon dérivé de l'horodatage)
        self.output_dir = output_dir
        self.prefix = prefix
        self.split_by_minute = split_by_minute
        self.suffix_format = suffix_format
        self.min_rows = min_rows
        self._minute = None
        self._file = None
        self._writer = None
        self._path = None
        self._rows = 0
        os.makedirs(output_dir, exist_ok=True)

    def _file_name(self, timestamp):
        # "{ts}" dans name est remplacé par l'heure de la première mesure : HHhMMmSS.mmms
        if self.name:
            ts = f"{timestamp[11:13]}h{timestamp[14:16]}m{timestamp[17:19]}.{timestamp[20:23]}s"
            return self.name.replace("{ts}", ts)
        return _minute_name(timestamp)

    def _unique_path(self, name):
        base = os.path.join(self.output_dir, f"{self.prefix}{name}")
        path = f"{base}.csv"
        i = 1
        while os.path.exists(path):
            path = f"{base}{self.suffix_format.format(i)}.csv"
            i += 1
        return path

    def write(self, timestamp, values):
        """timestamp : 'YYYY-MM-DD HH:MM:SS.mmm' ; values : 6 flottants."""
        # Une ligne série tronquée (caractères perdus) ne doit pas créer un faux fichier
        if not TIMESTAMP_RE.match(timestamp):
            return
        minute = timestamp[:16]
        if self._file is None or (self.split_by_minute and minute != self._minute):
            self.close()
            self._path = self._unique_path(self._file_name(timestamp))
            self._file = open(self._path, "w", newline="")
            self._writer = csv.writer(self._file)
            self._writer.writerow(HEADER)
            self._minute = minute
        self._writer.writerow([timestamp, *values])
        self._rows += 1

    def close(self):
        if self._file:
            self._file.close()
            if self._rows < self.min_rows:
                os.remove(self._path)
            self._file = self._writer = self._minute = self._path = None
            self._rows = 0
