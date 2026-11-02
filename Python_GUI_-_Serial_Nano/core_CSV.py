import csv
import os
import re

DEFAULT_OUTPUT_DIR = "recordings"  # Dossier de sortie personnalisable
HEADER = ["timestamp", "ax", "ay", "az", "gx", "gy", "gz"]
MIN_ROWS = 10  # Un fichier de moins de MIN_ROWS mesures est supprimé à la fermeture
TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}$")


class CSVRecorder:
    """Enregistre les mesures dans un CSV par date (celle de l'Arduino).
    Si le fichier d'une date existe déjà, un suffixe _1, _2... est ajouté."""

    def __init__(self, output_dir=DEFAULT_OUTPUT_DIR):
        self.output_dir = output_dir
        self._date = None
        self._file = None
        self._writer = None
        self._path = None
        self._rows = 0
        os.makedirs(output_dir, exist_ok=True)

    def _unique_path(self, date):
        path = os.path.join(self.output_dir, f"{date}.csv")
        i = 1
        while os.path.exists(path):
            path = os.path.join(self.output_dir, f"{date}_{i}.csv")
            i += 1
        return path

    def write(self, timestamp, values):
        """timestamp : 'YYYY-MM-DD HH:MM:SS.mmm' ; values : 6 flottants."""
        # Une ligne série tronquée (caractères perdus) ne doit pas créer un faux fichier
        if not TIMESTAMP_RE.match(timestamp):
            return
        date = timestamp[:10]
        if date != self._date:
            self.close()
            self._path = self._unique_path(date)
            self._file = open(self._path, "w", newline="")
            self._writer = csv.writer(self._file)
            self._writer.writerow(HEADER)
            self._date = date
        self._writer.writerow([timestamp, *values])
        self._rows += 1

    def close(self):
        if self._file:
            self._file.close()
            if self._rows < MIN_ROWS:
                os.remove(self._path)
            self._file = self._writer = self._date = self._path = None
            self._rows = 0
