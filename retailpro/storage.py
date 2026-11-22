"""File layer: JSON persistence with atomic writes, corruption recovery, CSV export."""
import csv
import json
import os
import shutil
import tempfile

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_data_dir = os.path.join(_BASE, "data")


def set_data_dir(path):
    global _data_dir
    _data_dir = path


def data_dir():
    os.makedirs(_data_dir, exist_ok=True)
    return _data_dir


def path_for(*parts):
    p = os.path.join(data_dir(), *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def load(name, default):
    """Read a JSON file; if missing return default; if corrupt keep a backup and return default."""
    p = path_for(name)
    if not os.path.exists(p):
        return default
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        shutil.copy(p, p + ".corrupt")
        return default


def save(name, data):
    """Write atomically (temp file + replace) so a crash can never corrupt saved data."""
    p = path_for(name)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    except OSError:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_text(folder, filename, text):
    p = path_for(folder, filename)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


def export_csv(filename, headers, rows):
    p = path_for("exports", filename)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)
    return p
