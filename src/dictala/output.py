"""Salida: portapapeles, pegado automatico y notificacion.

Cada dependencia degrada sola: sin wl-copy no hay texto, sin ydotool el texto
queda en el portapapeles, sin notify-send no hay aviso. Ninguna es critica.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from .log import log

# input-event-codes.h: KEY_LEFTCTRL 29, KEY_LEFTSHIFT 42, KEY_V 47.
CTRL_V = ["29:1", "47:1", "47:0", "29:0"]
CTRL_SHIFT_V = ["29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]


def ejecutar(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess:
    """Ejecuta un comando dejando rastro en el log."""
    log(f"ejecutando: {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, **kwargs)
        log(f"  ok: {' '.join(cmd)}" if r.returncode == 0 else f"  codigo {r.returncode}")
        return r
    except (OSError, subprocess.SubprocessError) as exc:
        log(f"  fallo: {' '.join(cmd)} ({type(exc).__name__})")
        raise


def disponible(programa: str) -> bool:
    return shutil.which(programa) is not None


def app_enfocada(compositor: str = "auto") -> str:
    """app_id de la ventana enfocada. '' si no se puede saber.

    compositor: 'niri' usa el IPC de niri; 'auto' lo intenta si esta instalado;
    'ninguno' no consulta nada. La deteccion NO esta probada en otros
    compositores: si no es niri, devuelve '' y se usa Ctrl+V.
    """
    if compositor == "ninguno":
        return ""
    if compositor == "auto" and not disponible("niri"):
        return ""
    try:
        r = subprocess.run(
            ["niri", "msg", "-j", "windows"], capture_output=True, text=True, timeout=3, check=True
        )
        for w in json.loads(r.stdout):
            if w.get("is_focused"):
                return str(w.get("app_id", "")).lower()
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        log(f"No pude leer la ventana enfocada: {type(exc).__name__}")
    return ""


def teclas_pegar(app: str, terminales: tuple[str, ...]) -> list[str]:
    """Ctrl+Shift+V en las terminales de la lista, Ctrl+V en el resto."""
    if terminales and app in terminales:
        log(f"App enfocada: {app} -> Ctrl+Shift+V")
        return CTRL_SHIFT_V
    log(f"App enfocada: {app or 'desconocida'} -> Ctrl+V")
    return CTRL_V


def al_portapapeles(texto: str) -> bool:
    if not disponible("wl-copy"):
        log("wl-copy no esta instalado: no puedo copiar. Instalá wl-clipboard.")
        return False
    ejecutar(["wl-copy"], input=texto.encode(), check=True)
    log(f"Portapapeles: {texto}")
    return True


def pegar(teclas: list[str]) -> bool:
    """Envia las teclas con ydotool. False si no esta disponible."""
    if not disponible("ydotool"):
        log("ydotool no esta instalado: el texto queda en el portapapeles.")
        return False
    # No se setea YDOTOOL_SOCKET a proposito: cliente y daemon usan el mismo
    # default ($XDG_RUNTIME_DIR/.ydotool_socket). Solo hace falta exportarlo si
    # se arranca ydotoold con --socket-path.
    try:
        ejecutar(["ydotool", "key", *teclas], check=True)
    except (OSError, subprocess.SubprocessError):
        return False
    return True


def notificar(texto: str) -> None:
    if not disponible("notify-send"):
        return
    try:
        ejecutar(["notify-send", "Dictado", texto], check=False)
    except (OSError, subprocess.SubprocessError):  # pragma: no cover
        pass


def entregar(texto: str, cfg) -> None:
    """Portapapeles siempre; pegado y notificacion si se puede."""
    if not texto.strip():
        log("Sin texto reconocido.")
        return
    if not al_portapapeles(texto):
        return
    if cfg.pegar:
        app = app_enfocada(cfg.compositor)
        teclas = teclas_pegar(app, cfg.terminales)
        if not pegar(teclas):
            log("Pega con Ctrl+V a mano.")
    else:
        log("Pegado automatico desactivado en la configuracion.")
    notificar(texto)
