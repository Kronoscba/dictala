"""Log con timestamp a stdout y a archivo.

Nunca debe tumbar el dictado: cualquier error de I/O se ignora.
"""

from __future__ import annotations

import os
import sys
import time

MAX_BYTES = 512 * 1024
_archivo: str | None = None


def configurar(ruta: str | None) -> None:
    global _archivo
    _archivo = ruta


def log(mensaje: str) -> None:
    linea = f"{time.strftime('%H:%M:%S')} {mensaje}"
    print(linea, flush=True)
    if not _archivo:
        return
    try:
        if os.path.exists(_archivo) and os.path.getsize(_archivo) > MAX_BYTES:
            os.remove(_archivo)
        with open(_archivo, "a") as f:
            f.write(linea + "\n")
    except OSError as exc:  # pragma: no cover - solo I/O
        print(f"aviso: no pude escribir el log ({exc})", file=sys.stderr)


def error(mensaje: str) -> None:
    log(mensaje)
