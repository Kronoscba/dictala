"""Audio: enumerate dispositivos, grabar con corte por silencio y resamplear.

Por que el resampleo va con PyAV y no con un promedio de N muestras: si el
dispositivo abre a 44100 Hz, dividir por 3 no lleva a 16000 y el audio llega
corrido a whisper. Ademas, faster-whisper NO resamplea los np.ndarray que le
pases (transcribe.py solo llama a decode_audio si la entrada no es un array),
asi que hay que entregarle 16000 Hz exactos.
"""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import numpy as np
import sounddevice as sd

from .config import TASAS_FALLBACK
from .log import log

TASA_WHISPER = 16000


def dispositivos() -> list[dict[str, Any]]:
    """Dispositivos de entrada que aceptan float32 mono."""
    return [
        {
            "indice": d["index"],
            "nombre": d["name"],
            "canales": d["max_input_channels"],
            "tasa": int(d["default_samplerate"]),
        }
        for d in sd.query_devices()
        if d["max_input_channels"] > 0
    ]


def es_placeholder(nombre: str) -> bool:
    """True si el 'dispositivo' no es un microfono real.

    PipeWire/ALSA publican fuentes de relleno ('Dummy Output') que PortAudio
    lista como entrada pero que no capturan nada. Es el caso tipico en una VM
    sin microfono: hay dispositivos, y ninguno sirve.
    """
    n = nombre.lower()
    return any(p in n for p in ("dummy", "null", "monitor", "loopback"))


def _coincide(dev: dict[str, Any], objetivo: str | int | None) -> bool:
    if objetivo is None:
        # Sin configurar: el del sistema (indice 'default' de PortAudio).
        return dev["nombre"].lower() == "default"
    if isinstance(objetivo, int):
        return dev["indice"] == objetivo
    objetivo = str(objetivo).lower()
    return dev["indice"] == objetivo or dev["nombre"].lower() == objetivo


def elegir_dispositivo(objetivo: str | int | None = None) -> dict[str, Any]:
    """Devuelve el dispositivo pedido, o el del sistema si no se especifico."""
    candidatos = dispositivos()
    if not candidatos:
        raise RuntimeError("No hay ningun dispositivo de entrada de audio.")
    for dev in candidatos:
        if _coincide(dev, objetivo):
            return dev
    nombres = ", ".join(f"{d['indice']}:{d['nombre']}" for d in candidatos)
    raise RuntimeError(f"No encontre el microfono {objetivo!r}. Disponibles: {nombres}")


def _stream(mic: str | int, tasa: int, blocksize: int, callback) -> sd.InputStream:
    return sd.InputStream(
        samplerate=tasa,
        channels=1,
        dtype="float32",
        device=mic,
        blocksize=blocksize,
        callback=callback,
    )


@contextmanager
def _silenciar_stderr():
    """Tapa la queja de PortAudio mientras abre el stream.

    PortAudio escribe a stderr desde C ('Expression 'r' failed in
    pa_linux_alsa.c...'), asi que redirect_stderr no alcanza: hay que mover el
    fd 2 de verdad.
    """
    try:
        nulo = os.open(os.devnull, os.O_WRONLY)
    except OSError:  # pragma: no cover - devnull siempre esta
        yield
        return
    guardado = os.dup(2)
    os.dup2(nulo, 2)
    try:
        yield
    finally:
        os.dup2(guardado, 2)
        os.close(guardado)
        os.close(nulo)


def abrir_stream(mic: str | int, tasa: int, blocksize: int, callback) -> tuple[sd.InputStream, int]:
    """Abre el stream probando tasas hasta que una funcione.

    PortAudio no convierte de tasa: si el dispositivo no admite la pedida,
    falla con 'Invalid sample rate'. Se prueban en orden y se devuelven el
    stream (ya abierto) y la tasa que sirvio. El caller debe cerrarlo.
    """
    candidatas = [tasa] if tasa else list(TASAS_FALLBACK)
    ultimo_error = None
    for intento in candidatas:
        try:
            with _silenciar_stderr():
                s = _stream(mic, intento, blocksize, callback)
                s.start()
            log(f"Stream abierto a {intento} Hz")
            return s, intento
        except Exception as exc:  # sd.PortAudioError y errores de open()
            ultimo_error = exc
            log(f"  {intento} Hz no sirve: {type(exc).__name__}")
    raise RuntimeError(f"Ninguna tasa sirvio para {mic!r}: {ultimo_error}")


def cerrar_stream(stream: sd.InputStream) -> None:
    try:
        stream.stop()
        stream.close()
    except Exception:  # pragma: no cover - cierre best-effort
        pass


def grabar(
    mic: str | int,
    tasa: int,
    blocksize: int,
    umbral: float,
    silencio_s: float,
    max_s: float,
    al_abrir: Callable[[], None] | None = None,
) -> tuple[np.ndarray | None, int]:
    """Graba hasta cortar por silencio. Devuelve (audio, tasa) o (None, tasa).

    al_abrir se invoca justo antes de abrir el stream: es donde conviene
    arrancar la carga del modelo en paralelo.
    """
    bloques: list[np.ndarray] = []
    st = {"silencio": None, "hablo": False, "parar": False}
    inicio = time.monotonic()

    def cb(indata, frames, t, status):  # noqa: ARG001
        if status:
            log(f"stream: {status}")
        bloques.append(indata.copy())
        rms = float(np.sqrt(np.mean(indata**2)))
        ahora = time.monotonic()
        if rms > umbral:
            st["hablo"] = True
            st["silencio"] = None
        elif st["silencio"] is None:
            st["silencio"] = ahora
        if st["parar"]:
            return
        if st["silencio"] and ahora - st["silencio"] >= silencio_s:
            log("Silencio, termino.")
            st["parar"] = True
        elif ahora - inicio >= max_s:
            log(f"Tope de {max_s}s.")
            st["parar"] = True

    if al_abrir:
        al_abrir()

    stream, usada = abrir_stream(mic, tasa, blocksize, cb)
    try:
        while not st["parar"]:
            time.sleep(0.05)
    finally:
        cerrar_stream(stream)

    total = sum(len(b) for b in bloques)
    log(f"Grabados {total / usada:.1f}s de audio ({len(bloques)} bloques)")
    if not st["hablo"]:
        log("No detecto voz, no transcribo.")
        return None, usada
    return np.concatenate(bloques, axis=0), usada


def resamplear(audio: np.ndarray, tasa: int, destino: int = TASA_WHISPER) -> np.ndarray:
    """Convierte a la tasa que espera whisper, con el resampler de FFmpeg.

    Techo conocido: devuelve ~16 muestras menos de las esperadas por el atraso
    del resampler. Irrelevante para ASR, pero no esperes len == duracion*16000.
    """
    audio = np.asarray(audio, dtype=np.float32)
    if tasa == destino:
        return audio
    from av.audio.resampler import AudioResampler

    resampler = AudioResampler(format="fltp", layout="mono", rate=destino)
    frame = av_frame_de(audio)
    frame.sample_rate = tasa
    partes = [f.to_ndarray().reshape(-1) for f in resampler.resample(frame)]
    if not partes:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(partes).astype(np.float32)


def av_frame_de(audio: np.ndarray):
    """Envuelve un array mono float32 en un av.AudioFrame."""
    import av

    return av.AudioFrame.from_ndarray(
        np.ascontiguousarray(audio.reshape(1, -1)), format="fltp", layout="mono"
    )


def medir_rms(mic: str | int, tasa: int, segundos: float, bloques: int = 256) -> list[float]:
    """Devuelve los RMS de `bloques` muestras consecutivas, para calibrar."""
    niveles: list[float] = []

    def cb(indata, frames, t, status):  # noqa: ARG001
        niveles.append(float(np.sqrt(np.mean(indata**2))))

    with (
        _silenciar_stderr(),
        sd.InputStream(
            samplerate=tasa,
            channels=1,
            dtype="float32",
            device=mic,
            blocksize=bloques,
            callback=cb,
        ),
    ):
        time.sleep(segundos)
    return niveles


def sugerir_umbral(niveles: list[float]) -> tuple[float, dict[str, float]]:
    """Sugiere un umbral a partir de niveles medidos.

    Usa el percentil 10 como piso de ruido y el 95 como voz, y se queda en el
    medio geometrico. Es una heuristica, no una medicion de SNR.
    """
    a = np.asarray(niveles, dtype=np.float64)
    if not a.size:
        raise ValueError("sin niveles medidos")
    ruido = float(np.percentile(a, 10))
    voz = float(np.percentile(a, 95))
    sugerido = float(np.sqrt(max(ruido, 1e-6) * max(voz, 1e-6)))
    estadisticas = {"ruido_p10": ruido, "voz_p95": voz, "pico": float(a.max())}
    return round(sugerido, 4), estadisticas
