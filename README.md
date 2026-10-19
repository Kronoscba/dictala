<div align="center" markdown="1">

[![Dictala](docs/logo.svg?v=2)](https://github.com/Kronoscba/dictala)

[![CI](https://github.com/Kronoscba/dictala/actions/workflows/ci.yml/badge.svg)](https://github.com/Kronoscba/dictala/actions/workflows/ci.yml)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?logo=python&logoColor=white)](pyproject.toml)
[![Plataforma](https://img.shields.io/badge/platform-Linux-lightgrey?logo=linux&logoColor=white)](#requisitos)
[![Compositor](https://img.shields.io/badge/compositor-cualquiera-blueviolet?logo=linux&logoColor=white)](#español)

**Dictado por voz global para Linux.**

[Español](#español) · [English](#english)

</div>

---

<a name="español"></a>

## Español

Pulsá una tecla, hablá, y el texto transcrito aparece donde tengas el cursor.
Funciona en Linux con cualquier compositor, usando Whisper (faster-whisper) en
CPU. Wayland y X11.

```
Tecla  ->  micrófono  ->  faster-whisper  ->  portapapeles + Ctrl+V
```

### Requisitos

| Necesario | Paquete en Arch | Para qué |
|---|---|---|
| Python 3.11+ | `python` | el intérprete |
| `portaudio` | `portaudio` | audio; lo requiere `sounddevice` |
| `wl-clipboard` | `wl-clipboard` | portapapeles en **Wayland** |
| `xclip` | `xclip` | portapapeles en **X11** (bspwm, i3, X11 puro) |
| `libnotify` | `libnotify` | notificación (opcional) |
| `ydotool` | `ydotool` | pegado automático (opcional) |
| `systemd` | `systemd` | tope de memoria (opcional) |

Bastan **uno** de `wl-clipboard` o `xclip`, según tu sesión. `dictala doctor`
te dice cuál encontró.

`sounddevice`, `numpy` y `faster-whisper` **no están en los repos de Arch**:
los instala el script dentro de su propio virtualenv.

<a name="compositores"></a>

### Qué funciona en qué

El fondo no depende del compositor:

- **`ydotool` inyecta por `uinput`**, o sea a nivel del kernel. No ve el
  compositor. Por eso el pegado automático funciona en todos.
- **Whisper** habla con el micrófono, no con la ventana.
- **El portapapeles** usa `wl-copy` en Wayland y cae a `xclip` o `xsel` en X11.

Lo único que cambia por compositor es **dos cosas**: el snippet para
agregar el atajo, y un detalle cosmético.

| | Atajo | Detecta la app enfocada |
|---|---|---|
| **niri** | `config.kdl` | `niri msg` |
| **Hyprland** | `hyprland.conf` | `hyprctl` |
| **Sway** | `~/.config/sway/config` | `swaymsg` |
| **i3** | `~/.config/i3/config` | `xdotool` |
| **bspwm** | `~/.config/bspwm/sxhkdrc` | `xdotool` |
| **GNOME** | `gsettings`, sin tecla libre | `xdotool` |
| **KDE** | atajo global, por GUI | `xdotool` |

Si tu compositor no está en la lista: `dictala` funciona igual. Lo único que
pierdes es el atajo (lo tenés que agregar a mano) y el pegado en terminales,
porque cae a `Ctrl+V` en vez de `Ctrl+Shift+V`. Lo único que **necesitás** es
poder lanzar el comando con una tecla, y eso lo hace cualquiera.

`install.sh` detecta el compositor y te imprime el snippet correcto. Los
snippets están todos más abajo por si los querés copiar a mano.

<a name="snippet-niri"></a>

#### niri

`~/.config/niri/config.kdl`, dentro del bloque `binds { }`:

```kdl
XF86Calculator repeat=false {
    spawn-sh "systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala"
}
```

`repeat=false` es **imprescindible**: sin eso, mantener la tecla lanza varias
transcripciones a la vez y eso puede matarte la sesión. Ver
[Importante](#importante).

#### Hyprland

`~/.config/hypr/hyprland.conf`:

```ini
bind = ,XF86Calculator,exec,systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

El modificador vacío (la `,` después de `bind`) es lo que dispara al apretar
en vez de al soltar. Es el equivalente de `repeat=false` en niri.

#### Sway

`~/.config/sway/config`:

```
bindsym XF86Calculator exec systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

#### i3

`~/.config/i3/config`. Mismo formato que Sway:

```
bindsym XF86Calculator exec systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

En i3 se relee con `i3-msg reload`, o `Mod+Shift+c` / `Mod+c` si no lo cambiaste.

#### bspwm

`~/.config/bspwm/sxhkdrc`. En sxhkd la tecla y el comando van en **dos
líneas**: la primera sin sangría, la segunda con cuatro espacios.

```
XF86Calculator
    systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

bspwm es X11, así que necesitás `xclip` en vez de `wl-clipboard`.

#### GNOME

GNOME sobre Wayland no permite atajos de tecla arbitraria. Los atajos globales
van por `gsettings`, en dos pasos:

```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/dictala/']"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:dictala /org/gnome/settings-daemon/plugins/media-keys/dictala/ command 'systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala'
```

Ojo: GNOME se reserva casi todos los atajos con tecla multimedia, y una
combinación simple tipo `Ctrl+Espacio` casi seguro pisa algo. Si podés, usá
una tecla sola.

#### KDE

Plasma no tiene una línea de config para atajos globales. Va por la GUI:
**Configuración del sistema → Teclado → Atajos → Global**, sumás un atajo y
en el comando ponés:

```
systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

### Instalación

```bash
git clone https://github.com/Kronoscba/dictala
cd dictala
./install.sh
```

El instalador verifica las dependencias, dice cuáles faltan y **no instala
nada sin que confirmes**. Después crea el virtualenv, instala el paquete y
habilita el servicio de usuario de `ydotool` si puede.

Al final imprime el snippet para tu compositor y te dice en qué archivo va. Los
snippets de cada uno están arriba, en [Qué funciona en qué](#compositores).

`install.sh` **no toca la config de tu compositor**. Ese snippet lo pegás vos.

<a name="que-tecla"></a>

### Qué tecla usar

`XF86Calculator` es la tecla **Calculadora**, la que dice **CALC** en muchos
teclados. Apretala, hablá, y el texto aparece donde tengas el cursor.

Si tu teclado no la tiene, usá la que quieras. Para descubrir el nombre de una
tecla:

```bash
wev    # niri, Sway, Hyprland (lo que esté en wlroots)
xev    # X11: bspwm, i3, GNOME, KDE
```

Apretá la tecla y mirá el nombre XKB que imprime (por ejemplo
`XF86AudioMicMute`). Eso es lo que va donde dice `XF86Calculator`.

Una alternativa si preferís no tocar la tecla: usá una combinación con
modificador, tipo `Mod+Space`. Eso evita las teclas que ya uses para otra cosa.

### Calibración

El umbral por defecto (`0.02`) está elegido para un micrófono USB normal. Si
dicta frases cortadas o no corta nunca:

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
compositor = "auto"    # auto | niri | hyprland | sway | x11 | ninguno
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

**`repeat=false`**. En niri los binds se repiten por defecto mientras los
mantengas apretados (con `repeat-rate 35/s`, ~35 veces por segundo). Cada
repetición lanza una transcripción completa. Varias en paralelo multiplican la
memoria y el OOM killer interviene.

En otros compositores el equivalente es disparar **al apretar y no al soltar**.
Hyprland: el modificador vacío (`bind = ,XF86Calculator,exec,...`). Sway e i3:
`bindsym` ya dispara al apretar, no hay que hacer nada.

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

**Probado además en contenedores, sin GPU ni micrófono:**

| Qué | Cómo | Qué se comprobó |
|---|---|---|
| `install.sh` en Debian 13 | contenedor limpio | instala las dependencias de punta a punta e imprime el snippet |
| X11 (bspwm) | Xvfb + bspwm real | detecta `x11`, saca la clase de `xprop`, `xclip` deja el texto en CLIPBOARD, `sxhkd` acepta el snippet y la tecla lo dispara |
| Wayland (sway) | sway headless | detecta `sway`, lee el `app_id` del árbol real de `swaymsg`, `wl-copy` deja el texto |
| `doctor` | en las dos sesiones | reporta el compositor correcto y el portapapeles que hay |

En esas pruebas no hay micrófono ni `ydotool`, así que el audio y el pegado
automático se ven solo como degradación: `Ctrl+V` y el texto en el
portapapeles.

**NO probado. No lo asumas:**

- **Hyprland de punta a punta.** No se pudo levantar en un contenedor: pide
  una GPU con KMS y un seat, y anidado tampoco arranca (weston 16 anuncia
  `wl_compositor` v5 y Hyprland pide v6). Su detector está cubierto por tests
  unitarios y por el contrato documentado de `hyprctl -j activewindow`
  (`{"class": ...}`), pero no por una sesión real.
- Otras distribuciones (Fedora, Ubuntu, NixOS). De Debian solo está probado
  `install.sh`.
- GPU (CUDA, ROCm)
- Modelos `medium` en adelante
- Más de un micrófono a la vez, o hotplug durante la grabación
- Idiomas distintos del español
- Micrófonos analógicos, Bluetooth, o que no abran a 48000 Hz

Con `compositor = "ninguno"` o en un compositor sin detector, `dictala` **cae a
`Ctrl+V` sin preguntar**. Ese camino es un fallback seguro, no una integración:
si tu terminal necesita `Ctrl+Shift+V`, ponela en `terminales` a mano.

### Desinstalar

```bash
./uninstall.sh
```

Borra el virtualenv, la configuración y deshabilita `ydotool.service`.
**No toca la config de tu compositor**: si agregaste el atajo, quitalo vos.

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
Works on Linux with any compositor, using Whisper (faster-whisper) on CPU.
Wayland and X11.

### Requirements

| Needed | Arch package | Why |
|---|---|---|
| Python 3.11+ | `python` | interpreter |
| `portaudio` | `portaudio` | audio; required by `sounddevice` |
| `wl-clipboard` | `wl-clipboard` | clipboard on **Wayland** |
| `xclip` | `xclip` | clipboard on **X11** (bspwm, i3, plain X11) |
| `libnotify` | `libnotify` | notification (optional) |
| `ydotool` | `ydotool` | automatic paste (optional) |
| `systemd` | `systemd` | memory cap (optional) |

You need **one** of `wl-clipboard` or `xclip`, depending on your session.
`dictala doctor` tells you which one it found.

`sounddevice`, `numpy` and `faster-whisper` are **not in the Arch repos**: the
installer puts them in its own virtualenv.

<a name="compositors"></a>

### What works where

The core does not depend on the compositor:

- **`ydotool` injects through `uinput`**, that is, at the kernel level. It never
  talks to the compositor. That is why automatic paste works everywhere.
- **Whisper** talks to the microphone, not to the window.
- **The clipboard** uses `wl-copy` on Wayland and falls back to `xclip` or
  `xsel` on X11.

Only two things change per compositor: **the snippet** to bind the key, and one
cosmetic detail.

| | Bind snippet | Focused-app detection |
|---|---|---|
| **niri** | `config.kdl` | `niri msg` |
| **Hyprland** | `hyprland.conf` | `hyprctl` |
| **Sway** | `~/.config/sway/config` | `swaymsg` |
| **i3** | `~/.config/i3/config` | `xdotool` |
| **bspwm** | `~/.config/bspwm/sxhkdrc` | `xdotool` |
| **GNOME** | `gsettings`, no free keys | `xdotool` |
| **KDE** | global shortcut, via GUI | `xdotool` |

If your compositor isn't in that list, `dictala` still works. All you lose is
the snippet (add the key yourself) and pasting into terminals, because it
falls back to `Ctrl+V` instead of `Ctrl+Shift+V`. The only thing you **need** is
the ability to launch a command with a key, and every compositor can do that.

`install.sh` detects your compositor and prints the right snippet. All the
snippets are below if you want to copy one by hand.

#### niri

`~/.config/niri/config.kdl`, inside `binds { }`:

```kdl
XF86Calculator repeat=false {
    spawn-sh "systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala"
}
```

`repeat=false` is **not optional**: without it, holding the key starts several
transcriptions at once and that can take your session down. See
[Important](#important).

#### Hyprland

`~/.config/hypr/hyprland.conf`:

```ini
bind = ,XF86Calculator,exec,systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

The empty modifier (the `,` after `bind`) is what fires on press instead of on
release. It's the equivalent of niri's `repeat=false`.

#### Sway

`~/.config/sway/config`:

```
bindsym XF86Calculator exec systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

#### i3

`~/.config/i3/config`. Same format as Sway:

```
bindsym XF86Calculator exec systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

Reload with `i3-msg reload`, or `Mod+Shift+c` / `Mod+c` if you never changed it.

#### bspwm

`~/.config/bspwm/sxhkdrc`. In sxhkd the key and the command go on **two lines**:
the first with no indentation, the second indented by four spaces.

```
XF86Calculator
    systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

bspwm is X11, so you need `xclip` instead of `wl-clipboard`.

#### GNOME

GNOME on Wayland doesn't allow arbitrary keybinds. Global shortcuts go through
`gsettings`, in two steps:

```bash
gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/dictala/']"
gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:dictala /org/gnome/settings-daemon/plugins/media-keys/dictala/ command 'systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala'
```

Watch out: GNOME reserves most multimedia-key shortcuts, and a simple
combination like `Ctrl+Space` will clash with something. If you can, use a
single key.

#### KDE

Plasma has no config line for global shortcuts. It's a GUI task: **System
Settings → Keyboard → Shortcuts → Global**, add a shortcut and put this in the
command field:

```
systemd-run --user --scope -q -p MemoryMax=2G ~/.local/share/dictala/venv/bin/dictala
```

### Install

```bash
git clone https://github.com/Kronoscba/dictala
cd dictala
./install.sh
```

The installer checks dependencies, reports what is missing and **installs
nothing without your confirmation**. It then creates the virtualenv, installs
the package and enables the `ydotool` user service if it can.

It prints the snippet for your compositor and tells you which file it goes in.
Every snippet is above, under [What works where](#compositors).

`install.sh` **does not touch your compositor config**. You paste that snippet.

### Which key to use

`XF86Calculator` is the **Calculator** key, the one labelled **CALC** on many
keyboards. Press it, speak, and the text lands wherever your cursor is.

If your keyboard doesn't have it, use whatever key you like. To find the name
of a key:

```bash
wev    # niri, Sway, Hyprland (anything on wlroots)
xev    # X11: bspwm, i3, GNOME, KDE
```

Press the key and read the XKB name it prints (for example
`XF86AudioMicMute`). That is what goes where `XF86Calculator` is.

If you'd rather not dedicate a single key, use a combination with a modifier,
like `Mod+Space`. That avoids keys you already use for something else.

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

Elsewhere the equivalent is firing **on press, not on release**. Hyprland: the
empty modifier (`bind = ,XF86Calculator,exec,...`). Sway and i3: `bindsym`
already fires on press, nothing to do.

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

**Also tested in containers, with no GPU and no microphone:**

| What | How | What was checked |
|---|---|---|
| `install.sh` on Debian 13 | clean container | installs dependencies end to end and prints the snippet |
| X11 (bspwm) | Xvfb + real bspwm | detects `x11`, reads the class via `xprop`, `xclip` puts the text in CLIPBOARD, `sxhkd` accepts the snippet and the key fires it |
| Wayland (sway) | headless sway | detects `sway`, reads `app_id` from the real `swaymsg` tree, `wl-copy` puts the text |
| `doctor` | in both sessions | reports the right compositor and the clipboard that exists |

Those containers have no microphone and no `ydotool`, so audio and automatic
pasting only show up as graceful degradation: `Ctrl+V` and the text sitting in
the clipboard.

**NOT tested — do not assume:**

- **Hyprland end to end.** It could not be brought up in a container: it wants
  a KMS-capable GPU plus a seat, and nesting it does not work either (weston 16
  advertises `wl_compositor` v5 and Hyprland asks for v6). Its detector is
  covered by unit tests and by the documented `hyprctl -j activewindow`
  contract (`{"class": ...}`), but not by a live session.
- Other distributions (Fedora, Ubuntu, NixOS). On Debian only `install.sh` was
  tested.
- GPUs (CUDA, ROCm)
- `medium` and up models
- More than one microphone at a time, or hotplug during recording
- Languages other than Spanish
- Analog or Bluetooth microphones

With `compositor = "ninguno"` or on a compositor with no detector, `dictala`
**falls back to `Ctrl+V` without asking**. That path is a safe fallback, not an
integration: if your terminal needs `Ctrl+Shift+V`, put it in `terminales`
yourself.

### Uninstall

```bash
./uninstall.sh
```

Removes the virtualenv and config, disables `ydotool.service`. **It does not
touch your compositor config**: if you added the keybind, remove it yourself.

### License

MIT.
