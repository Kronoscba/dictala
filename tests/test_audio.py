"""Tests de audio: resampleo, seleccion de microfono y sugerencia de umbral."""

from __future__ import annotations

import numpy as np
import pytest

from dictala import audio

SENOIDAL_HZ = 440


def senoidal(tasa: float, segundos: float) -> np.ndarray:
    t = np.arange(int(tasa * segundos)) / tasa
    return (0.5 * np.sin(2 * np.pi * SENOIDAL_HZ * t)).astype(np.float32)


@pytest.mark.parametrize("tasa", [16000, 32000, 44100, 48000])
def test_resamplear_llega_a_16000(tasa):
    audio_16k = audio.resamplear(senoidal(tasa, 0.5), tasa)
    assert audio_16k.dtype == np.float32
    # ~16 muestras de diferencia por el atraso del resampler de FFmpeg.
    esperado = int(16000 * 0.5)
    assert abs(len(audio_16k) - esperado) < 64


def test_resamplear_conserva_amplitud():
    """Un promediar sin filtro perderia energia; el resampler de FFmpeg no."""
    original = senoidal(48000, 0.5)
    resultado = audio.resamplear(original, 48000)
    assert np.abs(resultado).max() == pytest.approx(0.5, abs=0.05)


def test_resamplear_16k_devuelve_igual():
    original = senoidal(16000, 0.2)
    resultado = audio.resamplear(original, 16000)
    assert np.array_equal(resultado, original)


def test_sugerir_umbral_entre_ruido_y_voz():
    ruido = np.full(1000, 0.0005)
    voz = np.full(200, 0.2)
    niveles = np.concatenate([ruido, voz]).tolist()
    umbral, stats = audio.sugerir_umbral(niveles)
    assert 0.0005 < umbral < 0.2
    assert stats["ruido_p10"] == pytest.approx(0.0005, abs=0.0005)
    assert stats["pico"] == pytest.approx(0.2, abs=0.001)


def test_sugerir_umbral_sin_voz():
    """Si solo hay ruido, el umbral queda cerca del ruido (nada que cortar)."""
    niveles = (np.full(1000, 0.0004)).tolist()
    umbral, _ = audio.sugerir_umbral(niveles)
    assert 0.0 < umbral < 0.01


def test_sugerir_umbral_sin_datos():
    with pytest.raises(ValueError):
        audio.sugerir_umbral([])


# --- seleccion de microfono, con dispositivos simulados ---

DISPOSITIVOS = [
    {"indice": 0, "nombre": "HDA Intel PCH: CX20590 Analog (hw:0,0)", "canales": 2, "tasa": 44100},
    {"indice": 9, "nombre": "sysdefault", "canales": 128, "tasa": 48000},
    {"indice": 11, "nombre": "default", "canales": 128, "tasa": 44100},
    {"indice": 12, "nombre": "Jabra BIZ 1100 Mono", "canales": 1, "tasa": 48000},
    {"indice": 13, "nombre": "Audio Interno Estéreo analógico", "canales": 4, "tasa": 48000},
]


@pytest.fixture
def simulado(monkeypatch):
    monkeypatch.setattr(audio, "dispositivos", lambda: DISPOSITIVOS)


def test_elegir_por_nombre_exacto(simulado):
    dev = audio.elegir_dispositivo("Jabra BIZ 1100 Mono")
    assert dev["indice"] == 12
    assert dev["tasa"] == 48000


def test_elegir_por_indice(simulado):
    assert audio.elegir_dispositivo(12)["nombre"] == "Jabra BIZ 1100 Mono"


def test_elegir_sin_configurar_usa_el_default(simulado):
    assert audio.elegir_dispositivo(None)["nombre"] == "default"


def test_elegir_no_encuentra_da_error_util(simulado):
    with pytest.raises(RuntimeError) as exc:
        audio.elegir_dispositivo("Microfono Inexistente")
    # El error lista los disponibles para que el usuario pueda corregir.
    assert "Jabra BIZ 1100 Mono" in str(exc.value)


def test_elegir_sin_dispositivos(monkeypatch):
    monkeypatch.setattr(audio, "dispositivos", lambda: [])
    with pytest.raises(RuntimeError):
        audio.elegir_dispositivo(None)
