"""Tests de configuracion: defaults < TOML < entorno."""

from __future__ import annotations

import textwrap

from dictala import config


def escribir(tmp_path, contenido: str):
    ruta = tmp_path / "config.toml"
    ruta.write_text(textwrap.dedent(contenido), encoding="utf-8")
    return ruta


def test_defaults_sin_archivo(tmp_path, monkeypatch):
    monkeypatch.delenv("DICTALA_MODELO", raising=False)
    cfg = config.cargar(tmp_path / "no-existe.toml")
    assert cfg.modelo == "base"
    assert cfg.idioma == "es"
    assert cfg.umbral == 0.02
    assert cfg.silencio_s == 3.0
    assert cfg.terminales == ()
    assert cfg.compositor == "auto"
    assert cfg.origen["modelo"] == "default"


def test_lee_archivo_toml(tmp_path):
    ruta = escribir(
        tmp_path,
        """
        [voz]
        modelo = "tiny"
        umbral = 0.05

        [salida]
        terminales = ["foot", "alacritty"]
    """,
    )
    cfg = config.cargar(ruta)
    assert cfg.modelo == "tiny"
    assert cfg.umbral == 0.05
    assert cfg.terminales == ("foot", "alacritty")
    assert cfg.origen["modelo"] == "archivo"


def test_entorno_pisa_al_archivo(tmp_path, monkeypatch):
    ruta = escribir(tmp_path, '[voz]\nmodelo = "tiny"\n')
    monkeypatch.setenv("DICTALA_MODELO", "base")
    cfg = config.cargar(ruta)
    assert cfg.modelo == "base"
    assert cfg.origen["modelo"] == "env"


def test_archivo_ilegible_usa_default(tmp_path):
    ruta = escribir(tmp_path, "esto no es toml [[[")
    cfg = config.cargar(ruta)
    assert cfg.modelo == "base"


def test_tipos_desde_entorno_como_texto(tmp_path, monkeypatch):
    monkeypatch.setenv("DICTALA_UMBRAL", "0.03")
    monkeypatch.setenv("DICTALA_SILENCIO_S", "2.5")
    monkeypatch.setenv("DICTALA_PEGAR", "false")
    monkeypatch.setenv("DICTALA_TASA", "48000")
    cfg = config.cargar(tmp_path / "no-existe.toml")
    assert cfg.umbral == 0.03
    assert cfg.silencio_s == 2.5
    assert cfg.pegar is False
    assert cfg.tasa == 48000


def test_booleano_acepta_variantes(tmp_path, monkeypatch):
    for valor in ("1", "true", "si", "on", "YES"):
        monkeypatch.setenv("DICTALA_PEGAR", valor)
        assert config.cargar(tmp_path / "x.toml").pegar is True
    for valor in ("0", "false", "no", "off"):
        monkeypatch.setenv("DICTALA_PEGAR", valor)
        assert config.cargar(tmp_path / "x.toml").pegar is False


def test_terminales_por_coma(tmp_path, monkeypatch):
    monkeypatch.setenv("DICTALA_TERMINALES", "foot, wezterm ,")
    cfg = config.cargar(tmp_path / "x.toml")
    assert cfg.terminales == ("foot", "wezterm")


def test_dispositivo_numerico_se_convierte_a_int(tmp_path, monkeypatch):
    monkeypatch.setenv("DICTALA_DISPOSITIVO", "12")
    assert config.cargar(tmp_path / "x.toml").dispositivo == 12


def test_dispositivo_por_nombre_queda_texto(tmp_path, monkeypatch):
    monkeypatch.setenv("DICTALA_DISPOSITIVO", "Jabra BIZ 1100 Mono")
    assert config.cargar(tmp_path / "x.toml").dispositivo == "Jabra BIZ 1100 Mono"


def test_valor_ilegible_cae_a_default(tmp_path, monkeypatch):
    monkeypatch.setenv("DICTALA_UMBRAL", "no-es-un-numero")
    cfg = config.cargar(tmp_path / "x.toml")
    assert cfg.umbral == 0.02


def test_clave_desconocida_se_ignora(tmp_path):
    ruta = escribir(tmp_path, '[voz]\nmodelo = "tiny"\nclave_inventada = 1\n')
    cfg = config.cargar(ruta)
    assert cfg.modelo == "tiny"
    assert not hasattr(cfg, "clave_inventada")


def test_plantilla_es_toml_valido(tmp_path):
    """La plantilla que escribe init-config tiene que parsear."""
    ruta = tmp_path / "plantilla.toml"
    ruta.write_text(config.PLANTILLA, encoding="utf-8")
    cfg = config.cargar(ruta)
    assert cfg.modelo == "base"
    assert cfg.pegar is True


def test_rutas_log_y_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    cfg = config.cargar(tmp_path / "x.toml")
    assert cfg.ruta_log() == f"{tmp_path}/dictala.log"
    assert cfg.ruta_lock() == f"{tmp_path}/dictala.lock"


def test_log_y_lock_explicitos_ganan(tmp_path):
    ruta = escribir(tmp_path, '[sistema]\nlog = "/tmp/x.log"\nlock = "/tmp/x.lock"\n')
    cfg = config.cargar(ruta)
    assert cfg.ruta_log() == "/tmp/x.log"
    assert cfg.ruta_lock() == "/tmp/x.lock"
