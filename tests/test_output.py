"""Tests de salida: que teclas se mandan segun la app enfocada.

No se invoca ydotool ni ningun proceso real: solo se prueba la decision.
"""

from __future__ import annotations

import json
import subprocess

from dictala import output


class _Proceso:
    def __init__(self, stdout="", returncode=0):
        self.stdout = stdout
        self.returncode = returncode


def test_ctrl_v_por_defecto():
    assert output.teclas_pegar("brave", ()) == ["29:1", "47:1", "47:0", "29:0"]


def test_ctrl_shift_v_en_terminal_configurada():
    terminales = ("foot", "alacritty")
    assert output.teclas_pegar("foot", terminales) == [
        "29:1",
        "42:1",
        "47:1",
        "47:0",
        "42:0",
        "29:0",
    ]


def test_ctrl_v_en_app_no_lista():
    terminales = ("foot",)
    assert output.teclas_pegar("brave", terminales) == output.CTRL_V


def test_sin_lista_de_terminales_siempre_ctrl_v():
    """Con la lista vacia no se debe adivinar: Ctrl+V es el default seguro."""
    assert output.teclas_pegar("foot", ()) == output.CTRL_V


def test_app_desconocida_usa_ctrl_v():
    assert output.teclas_pegar("", ("foot",)) == output.CTRL_V


def test_keycodes_correctos():
    """29=KEY_LEFTCTRL, 42=KEY_LEFTSHIFT, 47=KEY_V (linux/input-event-codes.h)."""
    assert output.CTRL_V == ["29:1", "47:1", "47:0", "29:0"]
    assert output.CTRL_SHIFT_V == ["29:1", "42:1", "47:1", "47:0", "42:0", "29:0"]


# --- app_enfocada, con niri simulado ---

VENTANAS_NIRI = json.dumps(
    [
        {"id": 3, "app_id": "foot", "is_focused": False},
        {"id": 5, "app_id": "Noctalia", "is_focused": True},
    ]
)


def _simula(monkeypatch, stdout, returncode=0):
    def fake(cmd, **kwargs):  # noqa: ARG001
        return _Proceso(stdout, returncode)

    monkeypatch.setattr(subprocess, "run", fake)


def test_app_enfocada_lee_el_ipc_de_niri(monkeypatch):
    _simula(monkeypatch, VENTANAS_NIRI)
    assert output.app_enfocada("niri") == "noctalia"


def test_app_enfocada_compositor_ninguno_no_consulta(monkeypatch):
    def debe_fallar(cmd, **kwargs):  # noqa: ARG001
        raise AssertionError("no deberia consultar nada")

    monkeypatch.setattr(subprocess, "run", debe_fallar)
    assert output.app_enfocada("ninguno") == ""


def test_app_enfocada_auto_sin_niri_instalado(monkeypatch):
    monkeypatch.setattr(output, "disponible", lambda p: False)
    assert output.app_enfocada("auto") == ""


def test_app_enfocada_aguanta_json_invalido(monkeypatch):
    _simula(monkeypatch, "esto no es json")
    assert output.app_enfocada("niri") == ""


def test_app_enfocada_aguanta_error_de_niri(monkeypatch):
    def falla(cmd, **kwargs):  # noqa: ARG001
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", falla)
    assert output.app_enfocada("niri") == ""


def test_disponible_detecta_binario(monkeypatch):
    monkeypatch.setattr(
        output.shutil, "which", lambda p: "/usr/bin/wl-copy" if p == "wl-copy" else None
    )
    assert output.disponible("wl-copy") is True
    assert output.disponible("ydotool") is False
