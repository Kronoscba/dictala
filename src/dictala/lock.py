"""Lockfile no bloqueante: una sola instancia a la vez.

Por que existe: si dos pulsaciones arrancan dos transcripciones en paralelo,
Whisper multiplica la memoria. En niri el proceso vive en el cgroup de
niri.service, asi que el OOM killer mataria el script y systemd reiniciaria
la sesion entera. Ver README, seccion "Importante".
"""

from __future__ import annotations

import fcntl
import os
import time
from typing import IO


class Lock:
    """Descriptor del lock. Mantenerlo abierto mantiene el lock tomado."""

    def __init__(self, archivo: IO[str]):
        self._archivo = archivo

    def liberar(self) -> None:
        try:
            fcntl.flock(self._archivo, fcntl.LOCK_UN)
            self._archivo.close()
        except OSError:  # pragma: no cover
            pass


def tomar(ruta: str | None = None) -> Lock | None:
    """Toma el lock. Devuelve None si ya hay otra instancia.

    Con ruta None usa $XDG_RUNTIME_DIR/dictala.lock y cae a /tmp.
    """
    if ruta is None:
        base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
        ruta = os.path.join(base, "dictala.lock")
    try:
        archivo = open(ruta, "w")  # noqa: SIM115 - vive en el Lock
    except OSError:
        return None
    try:
        fcntl.flock(archivo, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        archivo.close()
        return None
    try:
        archivo.write(f"{os.getpid()} {time.strftime('%H:%M:%S')}\n")
        archivo.flush()
    except OSError:  # pragma: no cover
        pass
    return Lock(archivo)
