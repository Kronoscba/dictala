#!/usr/bin/env bash
# Instalador de dictala.
# - Verifica dependencias del sistema y dice cuales faltan. NO instala nada solo.
# - Crea el virtualenv e instala el paquete.
# - Habilita el servicio de usuario de ydotool, si puede, sin pedir sudo.
# - NO toca tu config de niri: imprime el snippet para que lo pegues vos.
#
# Idempotente: se puede volver a ejecutar sin romper nada.

set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${DICTALA_PREFIX:-$HOME/.local/share/dictala}"
VENV="$PREFIX/venv"
BIN="$VENV/bin"
MEMORIA="${DICTALA_MEMORIA:-2G}"

info()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
aviso() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
error(){ printf '\033[1;31mxx\033[0m %s\n' "$*" >&2; }
ok()    { printf '\033[1;32m ok\033[0m %s\n' "$*"; }

# --- 1. dependencias del sistema -------------------------------------------
info "Verificando dependencias del sistema"
FALTAN=()
declare -A PAQUETES=(
  [wl-copy]="wl-clipboard   (portapapeles)"
  [ydotool]="ydotool        (pegado automatico)"
  [notify-send]="libnotify    (notificaciones)"
  [systemd-run]="systemd      (limite de memoria, opcional)"
)
for prog in "${!PAQUETES[@]}"; do
  if command -v "$prog" >/dev/null 2>&1; then
    ok "$prog"
  else
    FALTAN+=("$prog")
  fi
done

if [ ${#FALTAN[@]} -gt 0 ]; then
  aviso "Falta:"
  for prog in "${FALTAN[@]}"; do
    echo "     $prog  ->  ${PAQUETES[$prog]}"
  done
  echo
  echo "  Instalalos con tu gestor de paquetes. En Arch:"
  echo "      sudo pacman -S wl-clipboard ydotool libnotify"
  echo
  read -r -p "  ¿Querés que intente instalarlos con pacman ahora? [s/N] " r || r="n"
  if [[ "${r,,}" == "s" ]] && command -v pacman >/dev/null 2>&1; then
    read -r -p "  Se va a usar sudo. ¿Confirmás? [s/N] " c || c="n"
    if [[ "${c,,}" == "s" ]]; then
      sudo pacman -S --needed --noconfirm wl-clipboard ydotool libnotify || \
        aviso "pacman fallo o se cancelo. Segui manualmente."
    fi
  else
    aviso "Seguis sin ellas. dictala va a funcionar igual, con menos funciones."
  fi
fi

# --- 2. grupo input, para ydotool ------------------------------------------
if [ -e /dev/uinput ]; then
  if id -nG | grep -qw input; then
    ok "perteneces al grupo 'input' (necesario para ydotoold)"
  else
    aviso "No perteneces al grupo 'input'. ydotoold no podria usar /dev/uinput."
    echo "     sudo usermod -aG input \$USER    y volve a iniciar sesion."
  fi
else
  aviso "/dev/uinput no existe. Cargá el modulo: sudo modprobe uinput"
fi

# --- 3. virtualenv ---------------------------------------------------------
if [ -x "$BIN/python" ]; then
  info "El virtualenv ya existe: $VENV"
else
  info "Creando virtualenv en $VENV"
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "$VENV"
  else
    python3 -m venv "$VENV"
  fi
fi

info "Instalando dictala"
if command -v uv >/dev/null 2>&1; then
  uv pip install --python "$BIN/python" "$RAIZ"
else
  "$BIN/python" -m pip install --upgrade pip
  "$BIN/python" -m pip install "$RAIZ"
fi
ok "instalado: $BIN/dictala"

# --- 4. configuracion ------------------------------------------------------
RUTA_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/dictala/config.toml"
if [ -f "$RUTA_CONFIG" ]; then
  info "Ya tenes configuracion en $RUTA_CONFIG (no se toco)"
else
  "$BIN/dictala" init-config || true
  ok "configuracion creada: $RUTA_CONFIG"
fi

# --- 5. ydotoold -----------------------------------------------------------
info "Habilitando el servicio de usuario de ydotool"
if ! systemctl --user list-unit-files >/dev/null 2>&1; then
  aviso "No puedo hablar con systemd de usuario (sesion sin DBus o headless)."
  echo "     Habilitalo vos dentro de tu sesion grafica:"
  echo "     systemctl --user enable --now ydotool.service"
elif ! systemctl --user list-unit-files ydotool.service >/dev/null 2>&1; then
  aviso "El paquete ydotool no esta instalado: no existe ydotool.service."
  echo "     El pegado automatico no va a funcionar. Texto al portapapeles, si."
else
  if systemctl --user enable --now ydotool.service >/dev/null 2>&1; then
    ok "ydotool.service habilitado y activo"
  else
    aviso "No pude habilitar ydotool.service. Probalo vos:"
    echo "     systemctl --user enable --now ydotool.service"
  fi
fi

# --- 6. snippet del compositor --------------------------------------------
cat <<EOF

$(printf '\033[1;32m')Listo.$(printf '\033[0m')

Para dictalar a mano:
    $BIN/dictala

Diagnostico y calibracion del microfono:
    $BIN/dictala doctor

Pegá esto en tu config de niri, dentro del bloque 'binds { }':

    // Dictado por voz.
    // repeat=false: sin esto, mantener la tecla lanza varias transcripciones
    // a la vez y eso puede matar tu sesion (ver README, seccion Importante).
    // spawn-sh: 'spawn' no pasa por shell, asi que con spawn el >> al log
    // no funciona y el script falla en silencio.
    // systemd-run --scope: saca el script del cgroup de niri.service y le
    // pone un tope de memoria.
    XF86Calculator repeat=false {
        spawn-sh "systemd-run --user --scope -q -p MemoryMax=$MEMORIA $BIN/dictala"
    }

Despues: niri msg action load-config-file
        (o reinicia la sesion)

El log queda en: \${XDG_RUNTIME_DIR:-/tmp}/dictala.log
EOF