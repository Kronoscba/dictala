<div align="center" markdown="1">

[![dictala](docs/logo.svg)](https://github.com/Kronoscba/dictala)

[![CI](https://github.com/Kronoscba/dictala/actions/workflows/ci.yml/badge.svg)](https://github.com/Kronoscba/dictala/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](pyproject.toml)
[![Plataforma](https://img.shields.io/badge/platform-Linux-lightgrey?logo=linux&logoColor=white)](#requisitos)
[![Compositor](https://img.shields.io/badge/compositor-niri-blueviolet?logo=niri&logoColor=white)](#español)

**Dictado por voz global para Wayland.**

[Español](#español) · [English](#english)

</div>

---

<a name="español"></a>

## Español

Pulsá una tecla, hablá, y el texto transcrito aparece donde tengas el cursor.
Funciona sobre Wayland con niri, usando Whisper (faster-whisper) en CPU.

```
Tecla  ->  micrófono  ->  faster-whisper  ->  portapapeles + Ctrl+V
```

### Requisitos

| Necesario | Paquete en Arch | Para qué |
|---|---|---|
| Python 3.11+ | `python` | el intérprete |
| `portaudio` | `portaudio` | audio; lo requiere `sounddevice` |
| `wl-clipboard` | `wl-clipboard` | poner el texto en el portapapeles |
| `libnotify` | `libnotify` | notificación (opcional) |
| `ydotool` | `ydotool` | pegado automático (opcional) |
| `systemd` | `systemd` | tope de memoria (opcional) |

`sounddevice`, `numpy` y `faster-whisper` **no están en los repos de Arch**:
los instala el script dentro de su propio virtualenv.

### Instalación

```bash
git clone https://github.com/Kronoscba/dictala
cd dictala
./install.sh
```

El instalador verifica las dependencias, dice cuáles faltan y **no instala
nada sin que confirmes**. Después crea el virtualenv, instala el paquete y
habilita el servicio de usuario de `ydotool` si puede.

Al final imprime el snippet para tu `config.kdl`. Pegalo dentro del bloque
`binds { }`:

```kdl
XF86Calculator repeat=false {
    spawn-sh "systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala"
}
```

Después: `niri msg action load-config-file`.

`install.sh` **no toca tu config de niri**. Ese snippet lo pegás vos.

### Calibración

El umbral por defecto (`0.02`) está elegido para un micrófono USB normal. Si
dicta phrases cortadas o no corta nunca:

```bash
dictala doctor
```

Eso lista tus micrófonos con sus tasas, verifica `ydotool`, y mide ruido de
fondo y voz durante unos segundos para **sugerirte un umbral**. Después
copialo a `~/.config/dictala/config.toml`.

### Configuración

`~/.config/dictala/config.toml`. Cada valor se sobrescribe con una variable
`DICTALA_<CAMPO>`, que tiene prioridad sobre el archivo.

```toml
[voz]
modelo = "base"        # tiny | base | small | medium | large-v3
idioma = "es"          # código de Whisper, o "auto"
umbral = 0.02          # RMS sobre el que se considera que hay voz
silencio_s = 3.0       # segundos de silencio que cortan la grabación
max_s = 30.0           # tope de seguridad

[mic]
dispositivo = null     # nombre exacto o índice; null = el del sistema
tasa = 0               # 0 = la que admita el dispositivo
blocksize = 4096

[salida]
pegar = true
terminales = ["foot"]  # apps que usan Ctrl+Shift+V

[sistema]
compositor = "auto"    # auto | niri | ninguno
```

### Qué modelos usar

Medido en la máquina de desarrollo (4 cores, sin GPU), clip de 8.8 s:

| Modelo | Transcripción | RAM | Español |
|---|---|---|---|
| `tiny` | 2.9 s | 331 MB | pierde tildes; confunde palabras |
| `base` | 5.4 s | 457 MB | correcto |
| `small` | 13.5 s | 1221 MB | **peor que `base`**: normaliza y pierde tildes |

`base` es el default por eso. `tiny` es más rápido pero en español confunde
palabras completas, no solo tildes.

Los modelos más grandes no sirven en CPU: `large-v3-turbo` tardó 97 s en un
clip de 8.8 s. Whisper siempre procesa una ventana de 30 segundos, así que el
costo casi no depende de cuánto hablaste.

<a name="importante"></a>

### Importante: por qué el snippet es así

No es decorativo. Sacale cualquiera de estas tres cosas y puede **matarte la
sesión**:

**`repeat=false`**. Los binds en niri se repiten por defecto mientras los
mantengas apretados (con `repeat-rate 35/s`, ~35 veces por segundo). Cada
repetición lanza una transcripción completa. Varias en paralelo multiplican la
memoria y el OOM killer interviene.

**`systemd-run --user --scope`**. Tu compositor suele ser un servicio systemd
de usuario. Un proceso lanzado desde un bind vive dentro de su cgroup. Cuando
el OOM killer mata a `dictala`, systemd concluye que el servicio afectado es
**el compositor**, y reinicia la sesión completa. Con `--scope`, el script corre
en su propia unidad y el OOM lo mata a él, no a tu escritorio.

**`MemoryMax`**. Es la última línea de defensa: si el script se pasa de
memoria, el OOM killer actúa dentro de su propia scope.

El `lockfile` interno (en `$XDG_RUNTIME_DIR/dictala.lock`) es la cuarta
protección: si ya hay una instancia corriendo, la segunda sale sin hacer nada.

### Problemas frecuentes

**`stream: input overflow` en el log.** PortAudio no [**llegó a tiempo** a leer
el búfer de audio. Suele pasar cuando la máquina está muy cargada al arrancar la
captura. Subí `blocksize` a 8192: menos callbacks de Python por segundo. Con
4096 no se observó ninguno en pruebas de 30 s.

**El texto queda en el portapapeles pero no se pega.** Casi siempre es
`ydotoold`:

```bash
systemctl --user status ydotool.service
dictala doctor          # verifica ydotoold y /dev/uinput
```

Si `ydotoold` no responde, habilitalo: `systemctl --user enable --now ydotool.service`.
Necesitás pertenecer al grupo `input`: `sudo usermod -aG input $USER` y volver
a iniciar sesión.

**Se corta la frase a mitad.** Bajá `silencio_s` o subí `umbral`.

**Nunca corta.** Subí `umbral` (probá 0.05) o corré `dictala doctor`.

**`Invalid sample rate`.** Tu micrófono no abre a la tasa configurada. Con
`tasa = 0` el script prueba 48000, 44100, 32000 y 16000 y usa la primera que
funcione.

**Cortes al empezar a hablar.** PortAudio necesita unos milisegundos para
arrancar. Hablá un instante después de pulsar la tecla.

### Por qué NO se usa `wtype`

`wtype` crea un teclado virtual por el protocolo `zwp_virtual_keyboard_v1`, pero
**nunca llama a `attach`**, y niri exige ese attach para saber a qué superficie
mandar las teclas. Además tiene issues abiertos en niri donde puede dejar la app
sin teclado ([#2314](https://github.com/niri-wm/niri/issues/2314)) o escribir
basura si cambia el foco ([#2280](https://github.com/niri-wm/niri/issues/2280)).

### Por qué NO se usa `ydotool type`

`ydotool type` **descarta los caracteres no ASCII**: tildes y `ñ` desaparecen.
Para dictado en español es inaceptable. Por eso usamos `ydotool key`, que manda
keycodes del kernel (`/usr/include/linux/input-event-codes.h`) y es
independiente del layout: `KEY_LEFTCTRL 29`, `KEY_LEFTSHIFT 42`, `KEY_V 47`.

### Qué está probado y qué no

**Probado en el equipo que lo desarrolló:**

| | |
|---|---|
| Sistema | Arch Linux |
| Compositor | niri 26.04 sobre Wayland |
| Micrófono | Jabra BIZ 1100 USB (mono, abre solo a 48000 Hz) |
| Cómputo | CPU de 4 cores, 8 GB de RAM, sin GPU |
| Distribución de teclado | anybody: se usan keycodes, no teclas |

**NO probado. No lo asumas:**

- Otras distribuciones (Fedora, Debian, Ubuntu, NixOS)
- Otros compositores: sway, Hyprland, GNOME, KDE, River
- Micrófonos analógicos, Bluetooth, o que no abran a 48000 Hz
- GPU (CUDA, ROCm)
- Modelos `medium` en adelante
- Más de un micrófono a la vez, o hotplug durante la grabación
- Idiomas distintos del español

Con `compositor = "ninguno"` o fuera de niri, `dictala` **cae a `Ctrl+V` sin
preguntar**. Ese camino **no está probado** en otros compositores: es un
fallback seguro, no una integración.

### Desinstalar

```bash
./uninstall.sh
```

Borra el virtualenv, la configuración y deshabilita `ydotool.service`.
**No toca tu config de niri**: si agregaste el bind, quitalo vos.

### Desarrollo

```bash
uv venv --python 3.12 .venv-dev
uv pip install --python .venv-dev/bin/python -e ".[dev]"
.venv-dev/bin/python -m pytest tests/ -q
.venv-dev/bin/python -m ruff check .
```

### Licencia

MIT. Las dependencias lo son también: `faster-whisper` MIT, `ctranslate2` MIT,
`sounddevice` MIT, `av` BSD-3-Clause, `numpy` BSD-3-Clause y otros.

---

<a name="english"></a>

## English

Press a key, speak, and the transcribed text appears wherever your cursor is.
Works on Wayland with niri, using Whisper (faster-whisper) on CPU.

### Requirements

| Needed | Arch package | Why |
|---|---|---|
| Python 3.11+ | `python` | interpreter |
| `portaudio` | `portaudio` | audio; required by `sounddevice` |
| `wl-clipboard` | `wl-clipboard` | put text on the clipboard |
| `libnotify` | `libnotify` | notification (optional) |
| `ydotool` | `ydotool` | automatic paste (optional) |
| `systemd` | `systemd` | memory cap (optional) |

`sounddevice`, `numpy` and `faster-whisper` are **not in the Arch repos**: the
installer puts them in its own virtualenv.

### Install

```bash
git clone https://github.com/Kronoscba/dictala
cd dictala
./install.sh
```

The installer checks dependencies, reports what is missing and **installs
nothing without your confirmation**. It then creates the virtualenv, installs
the package and enables the `ydotool` user service if it can.

It prints the snippet for your `config.kdl`. Paste it inside `binds { }`:

```kdl
XF86Calculator repeat=false {
    spawn-sh "systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala"
}
```

Then: `niri msg action load-config-file`.

`install.sh` **never touches your niri config**. You paste that snippet yourself.

### Calibrate

The default threshold (`0.02`) suits a normal USB microphone. If phrases get cut
or it never stops:

```bash
dictala doctor
```

It lists your microphones with their sample rates, checks `ydotool`, and
measures background noise and your voice for a few seconds to **suggest a
threshold**. Copy it into `~/.config/dictala/config.toml`.

### Configuration

`~/.config/dictala/config.toml`. Every value can be overridden by a
`DICTALA_<FIELD>` environment variable, which takes priority over the file.

### Model choice

Measured on the development machine (4 cores, no GPU), 8.8 s clip:

| Model | Transcription | RAM | Spanish |
|---|---|---|---|
| `tiny` | 2.9 s | 331 MB | drops accents; confuses words |
| `base` | 5.4 s | 457 MB | correct |
| `small` | 13.5 s | 1221 MB | **worse than `base`** |

`base` is the default for that reason. Bigger models are pointless on CPU:
`large-v3-turbo` took 97 s on the same clip. Whisper always processes a 30
second window, so cost barely depends on how long you spoke.

### Important: why the snippet looks like that

Remove any of the three and it can **kill your session**:

**`repeat=false`**. niri binds repeat by default while held. Each repeat starts
a full transcription; several in parallel multiply memory usage until the OOM
killer steps in.

**`systemd-run --user --scope`**. Your compositor is usually a systemd user
service, and a process spawned from a bind lives inside its cgroup. When the OOM
killer kills `dictala`, systemd concludes the affected service is **the
compositor** and restarts your whole session. With `--scope`, the script gets
its own unit and the OOM killer hits it instead.

**`MemoryMax`**. Last line of defence.

The internal lockfile (`$XDG_RUNTIME_DIR/dictala.lock`) is a fourth guard: if an
instance is already running, the second one exits silently.

### Troubleshooting

**`stream: input overflow` in the log.** PortAudio could not read the audio
buffer in time, usually when the machine is busy at capture start. Raise
`blocksize` to 8192 for fewer Python callbacks per second.

**Text lands on the clipboard but does not paste.** Almost always `ydotoold`:

```bash
systemctl --user status ydotool.service
dictala doctor
```

You need to be in the `input` group: `sudo usermod -aG input $USER`, then log
back in.

**Phrases cut in half.** Lower `silencio_s` or raise `umbral`.
**Never stops.** Raise `umbral` (try 0.05) or run `dictala doctor`.
**`Invalid sample rate`.** Your microphone does not open at the configured rate.
With `tasa = 0` the script tries 48000, 44100, 32000 and 16000.

### Why NOT `wtype`

`wtype` creates a virtual keyboard via `zwp_virtual_keyboard_v1` but **never
calls `attach`**, and niri requires it to know which surface to send keys to.
It also has open niri issues where it can leave an app without a keyboard
([#2314](https://github.com/niri-wm/niri/issues/2314)) or type garbage when focus
changes ([#2280](https://github.com/niri-wm/niri/issues/2280)).

### Why NOT `ydotool type`

`ydotool type` **drops non-ASCII characters**: accents and `ñ` vanish.
Unacceptable for Spanish dictation. Hence `ydotool key`, which sends kernel
keycodes (`/usr/include/linux/input-event-codes.h`) and is layout-independent.

### Tested and untested

**Tested on the development machine:** Arch Linux, niri 26.04 on Wayland, Jabra
BIZ 1100 USB microphone, 4-core CPU with 8 GB RAM and no GPU.

**NOT tested — do not assume:** other distributions; other compositors (sway,
Hyprland, GNOME, KDE, River); analog or Bluetooth microphones; GPUs; models
`medium` and up; more than one microphone at a time; hotplug during recording;
languages other than Spanish.

Outside niri, `dictala` **falls back to `Ctrl+V` without asking**. That path is
a safe fallback, not a tested integration.

### Uninstall

```bash
./uninstall.sh
```

Removes the virtualenv and config, disables `ydotool.service`. **It does not
touch your niri config**: if you added the bind, remove it yourself.

### License

MIT.
