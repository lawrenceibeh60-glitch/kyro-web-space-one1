"""backend/storage/atomic_writer.py - crash-safe JSON writes (tmp + fsync + os.replace, keeps .bak)."""
import json
import os
import shutil
from pathlib import Path


def write_json_atomic(path, data, backup=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    if backup and path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
    os.replace(tmp, path)


def read_json(path):
    """Read JSON; if the file is corrupt, fall back to the .bak copy."""
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        bak = path.with_name(path.name + ".bak")
        if bak.exists():
            with open(bak, "r", encoding="utf-8") as f:
                return json.load(f)
        raise
