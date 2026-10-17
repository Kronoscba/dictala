"""Punto de entrada de la linea de comandos.

dictala             dicta una vez (lo que dispara la tecla)
dictala doctor      diagnostico y calibracion
dictala config      muestra la configuracion en uso y de donde sale
dictala init-config escribe el archivo de configuracion con los defaults
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from . import audio, config, doctor, lock, log, output, transcribe


def dictar(cfg: config.Config) -> int:
    """Un ciclo completo: grabar, transcribir, entregar."""
    inicio = time.monotonic()
    log.configurar(cfg.ruta_log())
    log.log(f"--- inicio (pid {os.getpid()}) ---")

    taken = lock.tomar(cfg.ruta_lock())
    if taken is None:
        log.log("Ya hay una instancia corriendo, salgo.")
        return 0

    try:
        dev = audio.elegir_dispositivo(cfg.dispositivo)
        mic = dev["nombre"] if cfg.dispositivo is None else cfg.dispositivo
        log.log(f"Microfono: {dev['nombre']}")

        # La carga arranca aca, justo antes de abrir el stream, para que quede
        # oculta detras de los segundos de silencio.
        hilo, caja = transcribe.lanzar_carga(cfg.modelo)

        audio_real, tasa_usada = audio.grabar(
            mic,
            cfg.tasa,
            cfg.blocksize,
            cfg.umbral,
            cfg.silencio_s,
            cfg.max_s,
            al_abrir=hilo.start,
        )
        if audio_real is None:
            log.log("Sin voz: no espero al modelo ni transcribo.")
        else:
            audio16k = audio.resamplear(audio_real, tasa_usada)
            log.log(f"Audio listo: {len(audio16k) / 16000:.1f}s a 16000 Hz")
            texto = transcribe.transcribir(audio16k, hilo, caja, cfg.idioma)
            if texto:
                output.entregar(texto, cfg)
        log.log(f"--- fin en {time.monotonic() - inicio:.1f}s ---")
    except Exception as exc:  # noqa: BLE001
        log.error(f"ERROR: {type(exc).__name__}: {exc}")
        if isinstance(exc, RuntimeError) and audio.es_placeholder(mic):
            # Caso tipico en una VM: hay fuentes de relleno, ningun microfono.
            log.error(f"'{mic}' no es un microfono real. No hay nada que dictar.")
            log.error("Probalo en una maquina real, o corre: dictala doctor")
        if cfg.depurar:
            raise
        return 1
    finally:
        taken.liberar()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="dictala",
        description="Dictado por voz para Wayland.",
    )
    sub = parser.add_subparsers(dest="comando")
    d = sub.add_parser("doctor", help="diagnostico y calibracion")
    d.add_argument("--segundos", type=float, default=5.0)
    sub.add_parser("config", help="muestra la configuracion en uso")
    sub.add_parser("init-config", help="escribe el archivo de configuracion")
    args = parser.parse_args(argv)

    if args.comando == "doctor":
        return doctor.main(args.segundos)
    if args.comando == "config":
        doctor.mostrar_config()
        return 0
    if args.comando == "init-config":
        ruta = config.RUTA_CONFIG
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if ruta.exists():
            print(f"Ya existe: {ruta} (no se toco)")
            return 1
        ruta.write_text(config.PLANTILLA, encoding="utf-8")
        print(f"Escrito: {ruta}")
        return 0
    return dictar(config.cargar())


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
