"""Carga de configuracion: defaults < archivo TOML < variables de entorno.

Las variables de entorno se llaman DICTALA_<CAMPO> y ganan sobre el archivo.
El archivo acepta secciones ([voz], [mic], [salida], [sistema]) o claves sueltas.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

RUTA_CONFIG = Path(
    os.environ.get("DICTALA_CONFIG")
    or Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "dictala" / "config.toml"
)

VALOR_POR_DEFECTO: dict[str, Any] = {
    "modelo": "base",
    "idioma": "es",
    "umbral": 0.02,
    "silencio_s": 3.0,
    "max_s": 30.0,
    "pegar": True,
    "dispositivo": None,  # None = el que reporte el sistema
    "tasa": 0,  # 0 = la que admita el dispositivo
    "blocksize": 4096,
    "terminales": (),
    "compositor": "auto",  # auto | niri | ninguno
    "log": None,
    "lock": None,
    "depurar": False,
}

# Tasas a probar si el dispositivo no abre con la suya.
TASAS_FALLBACK = (48000, 44100, 32000, 16000)


@dataclass
class Config:
    modelo: str = "base"
    idioma: str = "es"
    umbral: float = 0.02
    silencio_s: float = 3.0
    max_s: float = 30.0
    pegar: bool = True
    dispositivo: str | int | None = None
    tasa: int = 0
    blocksize: int = 4096
    terminales: tuple[str, ...] = ()
    compositor: str = "auto"
    log: str | None = None
    lock: str | None = None
    depurar: bool = False
    origen: dict[str, str] = field(default_factory=dict)

    def ruta_log(self) -> str:
        return self.log or os.path.join(
            os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "dictala.log"
        )

    def ruta_lock(self) -> str:
        return self.lock or os.path.join(
            os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "dictala.lock"
        )


def _campos() -> list[str]:
    return [f.name for f in fields(Config) if f.name != "origen"]


def _del_archivo(ruta: Path) -> dict[str, Any]:
    if not ruta.is_file():
        return {}
    try:
        with open(ruta, "rb") as f:
            datos = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    plano: dict[str, Any] = {}
    for clave, valor in datos.items():
        if isinstance(valor, dict):
            plano.update(valor)
        else:
            plano[clave] = valor
    return plano


def _booleano(valor: Any) -> bool:
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("1", "true", "si", "sí", "yes", "on")


def _normalizar(clave: str, valor: Any) -> Any:
    if clave in ("umbral", "silencio_s", "max_s"):
        return float(valor)
    if clave in ("tasa", "blocksize"):
        return int(valor)
    if clave in ("pegar", "depurar"):
        return _booleano(valor)
    if clave == "terminales":
        if isinstance(valor, str):
            valor = valor.split(",")
        return tuple(str(v).strip().lower() for v in valor if str(v).strip())
    if clave == "dispositivo":
        texto = str(valor).strip()
        return int(texto) if texto.lstrip("-").isdigit() else texto
    return valor


def cargar(ruta: Path | None = None) -> Config:
    """Arma la configuracion final y deja en `origen` de donde salio cada valor."""
    ruta = ruta or RUTA_CONFIG
    campos = _campos()

    valores: dict[str, Any] = {}
    origen: dict[str, str] = {}

    for clave, valor in _del_archivo(ruta).items():
        if clave in campos:
            valores[clave] = valor
            origen[clave] = "archivo"

    for clave in campos:
        variable = f"DICTALA_{clave.upper()}"
        if variable in os.environ:
            valores[clave] = os.environ[variable]
            origen[clave] = "env"

    finales: dict[str, Any] = {}
    for clave, valor in valores.items():
        try:
            finales[clave] = _normalizar(clave, valor)
        except (TypeError, ValueError):
            origen.pop(clave, None)  # valor ilegible: se queda el default

    # origen queda completo: cada campo dice de donde sale, o "default".
    completo = {clave: origen.get(clave, "default") for clave in campos}
    return Config(origen=completo, **finales)


PLANTILLA = """\
# Configuracion de dictala.
# Cada valor se sobrescribe con una variable DICTALA_<CAMPO>.

[voz]
modelo = "base"        # tiny | base | small | medium | large-v3 | ...
idioma = "es"          # codigo de idioma de Whisper, o "auto"
umbral = 0.02          # RMS sobre el que se considera que hay voz
silencio_s = 3.0       # segundos de silencio que cortan la grabacion
max_s = 30.0           # tope de seguridad de la grabacion

[mic]
# Nombre exacto o indice, segun los muestra `dictala doctor`.
dispositivo = null
tasa = 0               # 0 = la que admita el dispositivo
blocksize = 4096       # menor = mas callbacks; mayor = menos overflows

[salida]
pegar = true           # pegar solo con Ctrl+V (necesita ydotool)
terminales = []        # apps que usan Ctrl+Shift+V en vez de Ctrl+V

[sistema]
compositor = "auto"    # auto | niri | ninguno
log = null             # null = $XDG_RUNTIME_DIR/dictala.log
lock = null
depurar = false
"""
