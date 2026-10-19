"""Tests de salida: copiadores del portapapeles y ventana enfocada.

Los detectores de compositor se prueban con JSON de mentira: lo que importa es
el parseo del arbol, no que haya un compositor corriendo.
"""

from __future__ import annotations

import subprocess

import pytest

from dictala import output


def _fake_run(monkeypatch, stdout="", returncode=0, por_comando=None):
    """Reemplaza subprocess.run y devuelve las llamadas que se hicieron."""

    def run(cmd, **kwargs):
        if por_comando is not None:
            por_comando.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout, "")
        return _check(cmd, returncode, stdout, "", kwargs.get("check"))

    monkeypatch.setattr(output.subprocess, "run", run)


def _check(cmd, returncode, stdout, stderr, check):
    """Como el subprocess.run real: con check=True y fallo, levanta."""
    r = subprocess.CompletedProcess(cmd, returncode, stdout, stderr)
    if check and returncode != 0:
        raise subprocess.CalledProcessError(returncode, cmd, stdout, stderr)
    return r


def _todo_instalado(monkeypatch):
    monkeypatch.setattr(output, "disponible", lambda p: True)


# --- portapapeles -----------------------------------------------------------


def test_usa_wl_copy_si_esta(monkeypatch):
    llamadas = []
    _fake_run(monkeypatch, por_comando=llamadas)
    _todo_instalado(monkeypatch)
    assert output.al_portapapeles("hola")
    assert llamadas[0] == ["wl-copy"]


def test_cae_a_xclip_en_x11_sin_wl_copy(monkeypatch):
    """Sin wl-copy (X11 puro) tiene que copiar igual, no rendirse."""
    llamadas = []
    _fake_run(monkeypatch, por_comando=llamadas)
    monkeypatch.setattr(output, "disponible", lambda p: p in ("xclip", "ydotool", "notify-send"))
    assert output.al_portapapeles("hola")
    assert llamadas[0] == ["xclip", "-selection", "clipboard"]


def test_cae_a_xsel_si_xclip_no_esta(monkeypatch):
    llamadas = []
    _fake_run(monkeypatch, por_comando=llamadas)
    monkeypatch.setattr(output, "disponible", lambda p: p == "xsel")
    assert output.al_portapapeles("hola")
    assert llamadas[0] == ["xsel", "--clipboard", "--input"]


def test_sigue_al_siguiente_si_uno_falla(monkeypatch):
    """wl-copy instalado pero roto no puede impedir que xclip funcione."""
    llamadas = []

    def run(cmd, **kwargs):
        llamadas.append(cmd)
        code = 1 if cmd[0] == "wl-copy" else 0
        return _check(cmd, code, "", "roto", kwargs.get("check"))

    monkeypatch.setattr(output.subprocess, "run", run)
    _todo_instalado(monkeypatch)
    assert output.al_portapapeles("hola")
    assert [c[0] for c in llamadas] == ["wl-copy", "xclip"]


def test_sin_copiadores_no_parte(monkeypatch):
    _fake_run(monkeypatch)
    monkeypatch.setattr(output, "disponible", lambda p: False)
    assert output.al_portapapeles("hola") is False


# --- ventana enfocada -------------------------------------------------------

# Arbol de sway real, recortado: la ventana enfocada esta al fondo y es
# XWayland, o sea que el id viene en window_properties.class y no en app_id.
ARBOL_SWAY = {
    "type": "root",
    "nodes": [
        {
            "type": "output",
            "nodes": [
                {
                    "type": "workspace",
                    "nodes": [
                        {"type": "con", "focused": False, "app_id": "code", "nodes": []},
                        {
                            "type": "floating_con",
                            "focused": True,
                            "app_id": None,
                            "window_properties": {"class": "URxvt", "instance": "urxvt"},
                            "nodes": [],
                        },
                    ],
                }
            ],
        }
    ],
}


def test_sway_encuentra_el_enfocado_anidado(monkeypatch):
    _fake_run(monkeypatch, stdout=__import__("json").dumps(ARBOL_SWAY))
    _todo_instalado(monkeypatch)
    assert output._app_sway() == "urxvt"


def test_sway_ignora_el_workspace_enfocado(monkeypatch):
    """El workspace puede venir focused: true; no es una ventana."""
    arbol = {"type": "root", "focused": True, "nodes": [{"type": "con", "app_id": "firefox"}]}
    _fake_run(monkeypatch, stdout=__import__("json").dumps(arbol))
    _todo_instalado(monkeypatch)
    assert output._app_sway() == ""


def test_hyprland_toma_el_class(monkeypatch):
    _fake_run(monkeypatch, stdout='{"class":"Alacritty","title":"zsh"}')
    _todo_instalado(monkeypatch)
    assert output._app_hyprland() == "alacritty"


def test_x11_saca_la_clase_de_wm_class(monkeypatch):
    """xdotool no tiene getwindowclassname: la clase sale de xprop."""
    llamadas = []

    def run(cmd, **kwargs):
        llamadas.append(cmd)
        if cmd[:2] == ["xdotool", "getactivewindow"]:
            return subprocess.CompletedProcess(cmd, 0, "10485772\n", "")
        return subprocess.CompletedProcess(cmd, 0, 'WM_CLASS(STRING) = "xterm", "XTerm"\n', "")

    monkeypatch.setattr(output.subprocess, "run", run)
    _todo_instalado(monkeypatch)
    assert output._app_x11() == "xterm"
    assert llamadas[1] == ["xprop", "-id", "10485772", "WM_CLASS"]


def test_x11_sin_wm_class(monkeypatch):
    _fake_run(monkeypatch, stdout="no such atom\n")
    _todo_instalado(monkeypatch)
    assert output._app_x11() == ""


def test_x11_sin_ventana_activa(monkeypatch):
    """Fuera de una sesion X, xdotool devuelve vacio y no hay que romper."""

    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, "", "no display")

    monkeypatch.setattr(output.subprocess, "run", run)
    _todo_instalado(monkeypatch)
    assert output._app_x11() == ""


def test_x11_necesita_xdotool_y_xprop(monkeypatch):
    """Con xdotool pero sin xprop el detector no esta disponible."""
    monkeypatch.setattr(output, "disponible", lambda p: p == "xdotool")
    assert output.app_enfocada("auto") == ""


def test_niri_toma_el_ventana_is_focused(monkeypatch):
    _fake_run(
        monkeypatch,
        stdout='[{"app_id":"foot","is_focused":false},{"app_id":"Gimp","is_focused":true}]',
    )
    _todo_instalado(monkeypatch)
    assert output._app_niri() == "gimp"


def test_auto_cae_en_cascada_hasta_uno_que_responda(monkeypatch):
    """niri instalado pero sin sesion niri: tiene que llegar a hyprland."""
    respuestas = {
        "niri": '{"error": "no niri"}',
        "hyprctl": '{"class":"kitty"}',
    }
    llamadas = []

    def run(cmd, **kwargs):
        llamadas.append(cmd)
        prog = cmd[0]
        if prog == "niri":
            return subprocess.CompletedProcess(cmd, 1, "", "no niri")
        return subprocess.CompletedProcess(cmd, 0, respuestas[prog], "")

    monkeypatch.setattr(output.subprocess, "run", run)
    monkeypatch.setattr(output, "disponible", lambda p: p in ("niri", "hyprctl"))
    assert output.app_enfocada("auto") == "kitty"
    assert llamadas[0][0] == "niri"


def test_compositor_ignorado_si_falla(monkeypatch):
    """Un IPC roto no puede tumbar la deteccion: se pasa al siguiente."""

    def run(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 1, "roto", "")

    monkeypatch.setattr(output.subprocess, "run", run)
    monkeypatch.setattr(output, "disponible", lambda p: True)
    assert output.app_enfocada("auto") == ""


def test_compositor_conocido_invalido_no_revienta(monkeypatch):
    _fake_run(monkeypatch)
    _todo_instalado(monkeypatch)
    assert output.app_enfocada("kwin-no-existe") == ""


def test_ninguno_no_consulta_nada(monkeypatch):
    llamadas = []
    _fake_run(monkeypatch, por_comando=llamadas)
    _todo_instalado(monkeypatch)
    assert output.app_enfocada("ninguno") == ""
    assert llamadas == []


@pytest.mark.parametrize(
    ("cfg", "esperado"),
    [(("kitty",), "29:1"), ((), "29:1")],
)
def test_teclas_segun_app(cfg, esperado):
    assert output.teclas_pegar("kitty", cfg)[0] == esperado


def test_terminal_usa_ctrl_shift_v():
    assert output.teclas_pegar("kitty", ("kitty",)) == output.CTRL_SHIFT_V
