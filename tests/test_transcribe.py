"""Tests de la transcripcion: el hilo del modelo y sus caminos de error."""

from __future__ import annotations

import threading
import time

import numpy as np

from dictala import transcribe


def test_lanzar_carga_crea_hilo_daemon():
    hilo, caja = transcribe.lanzar_carga("tiny")
    assert isinstance(hilo, threading.Thread)
    assert hilo.daemon, "el hilo debe ser daemon para no bloquear la salida"
    assert caja == {}


def test_carga_fallida_deja_error_en_la_caja():
    hilo, caja = transcribe.lanzar_carga("modelo-que-no-existe")
    hilo.start()
    hilo.join(timeout=60)
    assert "error" in caja
    assert "modelo" not in caja


def test_esperar_modelo_devuelve_none_si_fallo():
    hilo, caja = transcribe.lanzar_carga("modelo-que-no-existe")
    hilo.start()
    assert transcribe.esperar_modelo(hilo, caja) is None


def test_esperar_modelo_con_caja_ya_Lista():
    """Si el modelo ya estaba, no debe bloquear ni volver a cargar."""
    caja = {"modelo": object(), "carga": 1.0}
    assert transcribe.esperar_modelo(None, caja) is not None


def test_transcribir_con_error_no_rompe():
    hilo, caja = transcribe.lanzar_carga("modelo-que-no-existe")
    hilo.start()
    audio = np.zeros(16000, dtype=np.float32)
    assert transcribe.transcribir(audio, hilo, caja, "es") is None


def test_transcribir_con_audio_vacio_no_rompe():
    hilo, caja = transcribe.lanzar_carga("tiny")
    hilo.start()
    hilo.join(timeout=120)
    audio = np.zeros(0, dtype=np.float32)
    assert transcribe.transcribir(audio, hilo, caja, "es") is None


def test_transcribir_con_modelo_falso_no_toca_whisper():
    """Con un modelo stub se verifica el contrato sin cargar whisper real."""

    class ModeloStub:
        def transcribe(self, audio, language=None, vad_filter=False):  # noqa: ARG002
            self.visto = (audio, language, vad_filter)
            return iter([type("S", (), {"text": " hola mundo "})()]), None

    hilo = threading.Thread(target=lambda: None)
    caja = {"modelo": ModeloStub()}
    audio = np.zeros(160, dtype=np.float32)
    texto = transcribe.transcribir(audio, hilo, caja, "es")
    assert texto == "hola mundo"


def test_texto_vacio_devuelve_none():
    class ModeloVacio:
        def transcribe(self, audio, language=None, vad_filter=False):  # noqa: ARG002
            return iter([]), None

    hilo = threading.Thread(target=lambda: None)
    assert (
        transcribe.transcribir(
            np.zeros(160, dtype=np.float32), hilo, {"modelo": ModeloVacio()}, "es"
        )
        is None
    )


def test_idioma_auto_pasa_none():
    """Whisper detecta el idioma si language es None."""
    visto = {}

    class Modelo:
        def transcribe(self, audio, language=None, vad_filter=False):  # noqa: ARG002
            visto["language"] = language
            return iter([]), None

    hilo = threading.Thread(target=lambda: None)
    transcribe.transcribir(np.zeros(160, dtype=np.float32), hilo, {"modelo": Modelo()}, "auto")
    assert visto["language"] is None


def test_unjuntado_sin_espacios_dobles():
    """Los Segment.text traen espacio inicial; unir con ' ' duplicaba."""

    class Segmento:
        def __init__(self, t):
            self.text = t

    class Modelo:
        def transcribe(self, audio, language=None, vad_filter=False):  # noqa: ARG002
            return iter([Segmento(" primera"), Segmento(" segunda")]), None

    hilo = threading.Thread(target=lambda: None)
    texto = transcribe.transcribir(
        np.zeros(160, dtype=np.float32), hilo, {"modelo": Modelo()}, "es"
    )
    assert texto == "primera segunda"
    assert "  " not in texto


def test_hilo_no_bloquea_salida_sin_voz():
    """Sin voz no hay que esperar al hilo: el proceso debe poder salir."""
    inicio = time.monotonic()
    hilo, caja = transcribe.lanzar_carga("modelo-que-no-existe")
    hilo.start()
    # No esperamos: solo comprobamos que el hilo es daemon.
    assert hilo.daemon
    assert time.monotonic() - inicio < 1.0
    hilo.join(timeout=30)
