# Contributing to dictala

Gracias por querer colaborar. Este proyecto es chico y trata de ser
entendible de punta a punta.

## Entorno

```bash
uv venv --python 3.12 .venv-dev
uv pip install --python .venv-dev/bin/python -e ".[dev]"
```

Sin `uv`:

```bash
python3 -m venv .venv-dev
.venv-dev/bin/pip install -e ".[dev]"
```

## Antes de abrir un PR

```bash
.venv-dev/bin/python -m ruff check .
.venv-dev/bin/python -m pytest tests/ -q
shellcheck install.sh uninstall.sh
```

Las tres tienen que pasar. `ruff` y `shellcheck` también corren en CI.

## Qué se testea y qué no

CI corre **solo lo que no depende de hardware**: el resampleo de audio, la
selección de micrófono con dispositivos simulados, la decisión de `Ctrl+V` o
`Ctrl+Shift+V` con `niri` simulado, la carga de configuración y el lockfile.

**No** se testea el audio real, Wayland ni ydotool. Si tocás esa parte, agregá un
test de la lógica aislada y contá en el PR que no se puede verificar en CI.

## Reglas de implementación

- **El nombre del paquete va en minúscula.** `dictala` es el nombre del
  distribución, del comando (`dictala doctor`) y de la configuración
  (`~/.config/dictala/`), y eso no se toca. La marca **visual** es `Dictala`,
  con mayúscula, y vive en el logo (`docs/logo.svg`) y en los títulos de las
  secciones. No son la misma cosa.

- ** degrading es mejor que fallar.** Si falta `wl-copy`, `ydotool` o
  `notify-send`, `dictala` sigue funcionando con menos funciones y lo avisa.
  Un error de I/O en el log nunca debe tumbar el dictado.
- **Sin suposiciones sobre el hardware.** Nada de tasas fijas, nombres de
  micrófono ni umbrales calibrados en una máquina en particular.
- **El log va con timestamp** a stdout y al archivo. Si tocás una función que
  llama a un comando externo, dejá rastro de qué se ejecutó.
- **No rompas las protecciones.** El lockfile, `repeat=false`, el scope propio y
  `MemoryMax` existen por una razón documentada en el README. Si creés que
  alguno sobra, explicá por qué en el PR.
- **Comentarios en español**, código y nombres de función en inglés.

## Compatibilidad

El proyecto solo declara soporte para lo que está probado: Arch Linux, niri
sobre Wayland, CPU sin GPU, micrófono USB. Si agregás soporte para otra cosa,
decí en el PR **cómo lo probaste**. Ampliar la tabla del README sin evidencia
es un no.

## Commits y PRs

- Un tema por PR.
- Explicá el porqué, no solo el qué.
- Si tocás dependencias, actualizá `pyproject.toml` y justificá el salto.