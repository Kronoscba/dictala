"""Transcripcion: el modelo se carga en un hilo mientras se graba.

Por que en hilo: construir el modelo son ~1.5 s y el import de faster_whisper
~0.4 s. Sumados son ~1.9 s que, cargados despues de grabar, caen enteros entre
que el usuario termina de hablar y aparece el texto. Arrancando el hilo antes
de abrir el stream, la carga queda oculta detras de los segundos de silencio.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np

from .log import log


def lanzar_carga(modelo_nombre: str) -> tuple[threading.Thread, dict[str, Any]]:
    """Arranca la carga del modelo en un hilo daemon. Devuelve (hilo, caja).

    La caja es un dict compartido: el hilo escribe 'modelo' o 'error'.
    El hilo es daemon a proposito: si no se detecto voz, el proceso termina
    igual sin esperarlo. Nada queda residente entre pulsaciones.
    """
    caja: dict[str, Any] = {}

    def worker() -> None:
        try:
            t0 = time.monotonic()
            log(f"Cargando modelo ({modelo_nombre}, int8, cpu)...")
            # El import va aca adentro a proposito: son ~0.4 s que antes
            # pasaban fuera del log, entre "Silencio" y "Cargando modelo".
            from faster_whisper import WhisperModel

            caja["modelo"] = WhisperModel(modelo_nombre, device="cpu", compute_type="int8")
            caja["carga"] = time.monotonic() - t0
            log(f"Modelo cargado en {caja['carga']:.1f}s")
        except Exception as exc:
            caja["error"] = f"{type(exc).__name__}: {exc}"
            log(f"ERROR cargando el modelo: {caja['error']}")

    hilo = threading.Thread(target=worker, daemon=True, name="dictala-carga")
    return hilo, caja


def esperar_modelo(hilo: threading.Thread, caja: dict[str, Any]):
    """Devuelve el modelo, o None si la carga fallo."""
    if "modelo" not in caja:
        if "error" in caja:
            return None
        log("El modelo aun no termino de cargar, espero.")
        hilo.join()
    return caja.get("modelo")


def transcribir(
    audio16k: np.ndarray, hilo: threading.Thread, caja: dict[str, Any], idioma: str
) -> str | None:
    """Transcribe y devuelve el texto, o None si no se pudo."""
    modelo = esperar_modelo(hilo, caja)
    if modelo is None:
        log(f"Sin modelo, no transcribo. Error: {caja.get('error', 'desconocido')}")
        return None
    if audio16k.size == 0:
        log("Audio vacio, no transcribo.")
        return None

    t0 = time.monotonic()
    segmentos, _ = modelo.transcribe(
        audio16k, language=None if idioma in ("auto", "", "none") else idioma, vad_filter=True
    )
    # "" y no " ": cada Segment.text ya trae su espacio inicial, asi que unir
    # con " " deja un espacio doble entre frases.
    texto = "".join(s.text for s in segmentos).strip()
    log(f"Transcripcion: {time.monotonic() - t0:.1f}s")
    log(pico_memoria())
    return texto or None


def pico_memoria() -> str:
    """Memoria resident maxima del proceso, en MB."""
    import resource

    return f"Pico de memoria: {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024} MB"
