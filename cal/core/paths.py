import os
from pathlib import Path

def _xdg(env: str, default: str) -> Path:
    return Path(os.environ.get(env) or Path.home() / default)

def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "cal"

def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / "cal"

def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "cal"

def db_path() -> Path:
    return data_dir() / "cal.db"

def backups_dir() -> Path:
    return data_dir() / "backups"