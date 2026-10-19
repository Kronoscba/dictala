"""Salida: portapapeles, pegado automatico y notificacion.

Cada dependencia degrada sola: sin ningun copiador no hay texto, sin ydotool
el texto queda en el portapapeles, sin notify-send no hay aviso. Ninguna es
critica.

No se asume niri: el portapapeles cae a xclip/xsel en X11, y la ventana
enfocada se consulta por el IPC de cada compositor, con xdotool como
último recurso para X11 y XWayland.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any

from .log import log

# WM_CLASS de X11: "instancia", "Clase". La clase es la segunda.
_RE_WM_CLASS = re.compile(r'=\s*"([^"]*)"(?:\s*,\s*"([^"]*)")?')

# input-event-codes.h: KEY_LEFTCTRL 29, KEY_LEFTSHIFT 42, KEY_V 47.
CTRL_V = ["29:1", "47:1", "47:0", "29:0"]
CTRL_SHIFT_V = ["29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]

# (programa, argv, de donde sale). En orden: primero el nativo de Wayland.
# xclip se queda en background sirviendo la seleccion, asi que alcanza con
# esperar a que salga.
COPIADORES = (
    ("wl-copy", ["wl-copy"], "wl-clipboard (Wayland)"),
    ("xclip", ["xclip", "-selection", "clipboard"], "xclip (X11)"),
    ("xsel", ["xsel", "--clipboard", "--input"], "xsel (X11)"),
)


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


def copiadores_disponibles() -> list[str]:
    """Nombres de los programas que pueden poner texto en el portapapeles."""
    return [prog for prog, _, _ in COPIADORES if disponible(prog)]


# --- ventana enfocada, un detector por compositor ----------------------------


def _json(cmd: list[str]) -> Any:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=3, check=True)
    return json.loads(r.stdout)


def _app_niri() -> str:
    for w in _json(["niri", "msg", "-j", "windows"]):
        if w.get("is_focused"):
            return str(w.get("app_id", "")).lower()
    return ""


def _app_hyprland() -> str:
    return str(_json(["hyprctl", "-j", "activewindow"]).get("class", "")).lower()


def _enfocado_sway(nodo: Any) -> str:
    """Busca el nodo enfocado. El arbol es anidado, no plano."""
    if not isinstance(nodo, dict):
        return ""
    if nodo.get("focused") and nodo.get("type") in ("con", "floating_con"):
        props = nodo.get("window_properties") or {}
        # app_id para xdg-shell; window_properties.class para XWayland.
        return str(nodo.get("app_id") or props.get("class") or "").lower()
    for hijo in [*(nodo.get("nodes") or []), *(nodo.get("floating_nodes") or [])]:
        app = _enfocado_sway(hijo)
        if app:
            return app
    return ""


def _app_sway() -> str:
    return _enfocado_sway(_json(["swaymsg", "-t", "get_tree"]))


def _app_x11() -> str:
    """Clase de la ventana activa de X11. Sirve para bspwm, i3 y XWayland.

    xdotool no expone getwindowclassname en el CLI (esta en la libreria C pero
    el subcomando no existe), asi que la clase se lee con xprop. Formato:
        WM_CLASS(STRING) = "xterm", "XTerm"
    La segunda es la clase (ICCCM); la primera es la instancia.
    """
    r = subprocess.run(["xdotool", "getactivewindow"], capture_output=True, text=True, timeout=3)
    if r.returncode != 0 or not r.stdout.strip():
        return ""
    ventana = r.stdout.strip().splitlines()[0]
    p = subprocess.run(
        ["xprop", "-id", ventana, "WM_CLASS"], capture_output=True, text=True, timeout=3
    )
    if p.returncode != 0:
        return ""
    m = _RE_WM_CLASS.search(p.stdout)
    if not m:
        return ""
    return (m.group(2) or m.group(1)).lower()


# (nombre para la config, binarios que hacen falta, funcion)
DETECTORES: dict[str, tuple[tuple[str, ...], Any]] = {
    "niri": (("niri",), _app_niri),
    "hyprland": (("hyprctl",), _app_hyprland),
    "sway": (("swaymsg",), _app_sway),
    "x11": (("xdotool", "xprop"), _app_x11),
}


def detectar_compositor() -> str:
    """Primer compositor cuyo IPC responde de verdad. '' si ninguno.

    Importa 'responde' y no 'esta instalado': tener hyprctl en el PATH no
    significa que estes corriendo Hyprland, y confundirse de compositor
    manda a preguntar al que no es.
    """
    for nombre, (programas, fn) in DETECTORES.items():
        if not all(disponible(p) for p in programas):
            continue
        try:
            if fn():
                return nombre
        except (OSError, subprocess.SubprocessError, ValueError, KeyError):
            continue
    return ""


def app_enfocada(compositor: str = "auto") -> str:
    """app_id de la ventana enfocada. '' si no se puede saber.

    compositor: 'auto' prueba los detectores en orden; un nombre concreto usa
    solo ese; 'ninguno' no consulta nada. Si nada responde devuelve '' y se
    pega con Ctrl+V, que es lo correcto en casi todas las apps.
    """
    if compositor == "ninguno":
        return ""
    nombres = list(DETECTORES) if compositor == "auto" else [compositor]
    for nombre in nombres:
        entrada = DETECTORES.get(nombre)
        if entrada is None:
            log(f"Compositor desconocido en la config: {nombre!r}")
            continue
        programas, fn = entrada
        if not all(disponible(p) for p in programas):
            continue
        try:
            app = fn()
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
            log(f"{nombre}: no pude leer la ventana enfocada ({type(exc).__name__})")
            continue
        if app:
            log(f"{nombre}: app enfocada = {app}")
            return app
    return ""


def teclas_pegar(app: str, terminales: tuple[str, ...]) -> list[str]:
    """Ctrl+Shift+V en las terminales de la lista, Ctrl+V en el resto."""
    if terminales and app in terminales:
        log(f"App enfocada: {app} -> Ctrl+Shift+V")
        return CTRL_SHIFT_V
    log(f"App enfocada: {app or 'desconocida'} -> Ctrl+V")
    return CTRL_V


def al_portapapeles(texto: str) -> bool:
    """Copia el texto con lo que haya: wl-copy en Wayland, xclip o xsel en X11."""
    for programa, cmd, origen in COPIADORES:
        if not disponible(programa):
            continue
        try:
            ejecutar(cmd, input=texto.encode(), check=True)
        except (OSError, subprocess.SubprocessError):
            log(f"{programa} fallo; pruebo el siguiente copiador.")
            continue
        log(f"Portapapeles ({origen}): {texto}")
        return True
    log("Ningun copiador disponible: no puedo copiar el texto.")
    log("Instalá wl-clipboard (Wayland) o xclip (X11).")
    return False


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
