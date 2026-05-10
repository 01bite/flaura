from __future__ import annotations

import os
import stat
import sys
from pathlib import Path


def get_history_path() -> Path:
    path = Path.home() / ".flaura" / "history.txt"
    path.parent.mkdir(parents=True, exist_ok=True)

    # Touch the file with mode 0o600 if it doesn't exist; tighten perms if it does.
    if not path.exists():
        # os.open guarantees the file is created with these permissions atomically,
        # avoiding a window where it exists with default 0o644.
        fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL, 0o600)
        os.close(fd)
    else:
        try:
            current = stat.S_IMODE(path.stat().st_mode)
            if current & 0o077:
                path.chmod(0o600)
        except OSError as e:
            sys.stderr.write(f"[flaura] could not lock down {path}: {e}\n")

    return path
