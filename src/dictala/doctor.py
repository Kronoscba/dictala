"""Diagnostico y calibracion: `dictala doctor`."""

from __future__ import annotations

import os
import shutil
import subprocess

from . import audio, config, log
from .audio import es_placeholder

DEPENDENCIAS = {
    "wl-copy": "portapapeles (paquete: wl-clipboard)",
    "ydotool": "pegado automatico (paquete: ydotool)",
    "notify-send": "notificaciones (paquete: libnotify)",
    "systemd-run": "limite de memoria (paquete: systemd)",
    "niri": "deteccion de la app enfocada (opcional)",
}


def _titulo(t: str) -> None:
    print(f"\n== {t} ==")


def _estado(ok: bool) -> str:
    return "OK " if ok else "FALTA"


def revisar_dependencias() -> bool:
    _titulo("Dependencias del sistema")
    todo_ok = True
    for programa, para_que in DEPENDENCIAS.items():
        ok = shutil.which(programa) is not None
        if programa == "niri":
            ok = True  # opcional
        todo_ok = todo_ok and ok
        print(f"  [{_estado(ok)}] {programa:<12} {para_que}")
    return todo_ok


def revisar_ydotoold() -> bool:
    _titulo("ydotoold (daemon de inyeccion de teclas)")
    try:
        r = subprocess.run(["ydotool", "debug"], capture_output=True, text=True, timeout=5)
        combined = r.stdout + r.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"  no pude ejecutar `ydotool debug`: {type(exc).__name__}")
        return False
    # Chequeo positivo: ydotool solo imprime 'fd_daemon_socket' si se
    # conecto al daemon. Parsear un error en ingles es fragil.
    if "fd_daemon_socket" in combined:
        print("  ydotoold responde.")
        return True
    print("  ydotoold NO esta corriendo. Habilitalo con:")
    print("    systemctl --user enable --now ydotool.service")
    print("  Si el servicio arranca y esto sigue asi, casi siempre es que no")
    print("  perteneces al grupo 'input' y no puede abrir /dev/uinput:")
    print("    sudo usermod -aG input $USER   y volve a iniciar sesion")
    print("  Sin ydotoold el texto va al portapapeles igual, pero no se pega solo.")
    return False


def revisar_uinput() -> bool:
    _titulo("/dev/uinput (necesario por ydotoold)")
    ruta = "/dev/uinput"
    if not os.path.exists(ruta):
        print(f"  [FALTA] {ruta}")
        return False
    try:
        import grp

        stat = os.stat(ruta)
        grupo = grp.getgrgid(stat.st_gid).gr_name
    except (OSError, KeyError):
        grupo = "?"
    mis_grupos = set(os.getgroups())
    print(f"  [OK  ] {ruta}  grupo={grupo}")
    if grupo not in mis_grupos:
        print(f"  aviso: no perteneces al grupo '{grupo}'. Sumate con:")
        print(f"    sudo usermod -aG {grupo} $USER   y volve a iniciar sesion")
        return False
    print(f"  OK: perteneces al grupo '{grupo}'.")
    return True


def listar_microfonos() -> None:
    _titulo("Microfonos de entrada")
    try:
        dispositivos = audio.dispositivos()
    except Exception as exc:  # noqa: BLE001 -sondeamos
        print(f"  no pude enumerar: {type(exc).__name__}: {exc}")
        return
    if not dispositivos:
        print("  no hay dispositivos de entrada.")
        return
    print(f"  {'idx':>4}  {'tasa':>6}  {'canales':>7}  nombre")
    for d in dispositivos:
        cola = "   <- no es un microfono real" if es_placeholder(d["nombre"]) else ""
        print(f"  {d['indice']:>4}  {d['tasa']:>6}  {d['canales']:>7}  {d['nombre']}{cola}")


def probar_microfono(cfg) -> bool:
    """Abre el microfono que se usaria y, si no puede, dice por que."""
    _titulo("Prueba de captura")
    try:
        dev = audio.elegir_dispositivo(cfg.dispositivo)
    except RuntimeError as exc:
        print(f"  {exc}")
        print("  No hay ningun microfono de entrada. Conectalo y volve a probar.")
        return False
    print(f"  dispositivo: {dev['nombre']}")
    if es_placeholder(dev["nombre"]):
        print(f"  '{dev['nombre']}' no es un microfono real, es un dispositivo de")
        print("  relleno. En una VM, o sin microfono conectado, esto es todo lo")
        print("  que hay: el dictado no puede funcionar. Probalo en una máquina real.")
        return False
    try:
        stream, tasa = audio.abrir_stream(dev["nombre"], cfg.tasa, cfg.blocksize, lambda *a: None)
    except RuntimeError as exc:
        print(f"  lo veo en la lista pero no abre: {exc}")
        print("  Suele ser ALSA/PipeWire sin fuente por defecto. Fijate con:")
        print("    pactl list short sources")
        return False
    audio.cerrar_stream(stream)
    print(f"  OK: abre a {tasa} Hz.")
    return True


def calibrar(segundos: float = 5.0) -> None:
    """Mide ruido y voz para sugerir un umbral."""
    _titulo(f"Calibracion ({segundos:g}s): Primero guarda silencio, despues habla")
    cfg = config.cargar()
    try:
        dev = audio.elegir_dispositivo(cfg.dispositivo)
        stream = audio.abrir_stream(dev["nombre"], cfg.tasa, cfg.blocksize, lambda *a: None)
        tasa = stream["tasa"]
    except Exception as exc:  # noqa: BLE001
        print(f"  no pude abrir el microfono: {exc}")
        return
    print(f"  usando: {dev['nombre']} @ {tasa} Hz")
    print("  hablá cuando te avise...")
    niveles = audio.medir_rms(dev["nombre"], tasa, segundos)
    if not niveles:
        print("  no se capturo audio.")
        return
    umbral, stats = audio.sugerir_umbral(niveles)
    print(f"  ruido (p10) : {stats['ruido_p10']:.5f}")
    print(f"  voz   (p95) : {stats['voz_p95']:.5f}")
    print(f"  pico        : {stats['pico']:.5f}")
    print(f"  umbral actual: {cfg.umbral}")
    print(f"  umbral sugerido: {umbral}")
    if cfg.umbral < stats["ruido_p10"] * 3:
        print("  aviso: tu umbral esta cerca del ruido de fondo. Subi el umbral.")
    if cfg.umbral > stats["voz_p95"]:
        print("  aviso: tu umbral esta por encima de la voz. Bajalo.")


def mostrar_config() -> None:
    _titulo("Configuracion en uso")
    cfg = config.cargar()
    for campo in sorted(f for f in cfg.__dataclass_fields__ if f != "origen"):
        valor = getattr(cfg, campo)
        print(f"  {campo:<12} = {valor!r:<40} [{cfg.origen.get(campo, 'default')}]")


def main(segundos: float = 5.0) -> int:
    log.callar()  # el informe de doctor es el que importa, no el log del dictado
    print("dictala doctor - diagnostico y calibracion")
    print(f"  config: {config.RUTA_CONFIG} (existe: {config.RUTA_CONFIG.is_file()})")
    revisar_dependencias()
    revisar_ydotoold()
    revisar_uinput()
    listar_microfonos()
    probar_microfono(config.cargar())
    mostrar_config()
    if os.environ.get("DICTALA_SALTAR_CALIBRACION") != "1":
        _titulo("Calibracion opcional")
        print("  (poné DICTALA_SALTAR_CALIBRACION=1 para omitirla)")
        calibrar(segundos)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
