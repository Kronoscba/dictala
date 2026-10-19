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

# Cada requisito: "etiqueta|programas que lo satisfacen|pkg arch|pkg debian|pkg fedora"
# El portapapeles tiene tres: en Wayland va wl-copy, en X11 xclip o xsel.
REQUISITOS=(
  "portapapeles|wl-copy,xclip,xsel|wl-clipboard|wl-clipboard|wl-clipboard"
  "pegado automatico|ydotool|ydotool|ydotool|ydotool"
  "notificaciones|notify-send|libnotify|libnotify-bin|libnotify"
  "tope de memoria|systemd-run|systemd|systemd|systemd"
)

nombre_de_familia() {
  if command -v pacman >/dev/null 2>&1; then echo arch
  elif command -v apt-get >/dev/null 2>&1; then echo deb
  elif command -v dnf >/dev/null 2>&1; then echo fedora
  else echo ninguno
  fi
}

FAMILIA="$(nombre_de_familia)"
FALTAN_PAQ=()
for req in "${REQUISITOS[@]}"; do
  IFS='|' read -r etiqueta progs pa pa_deb pa_fed <<<"$req"
  case "$FAMILIA" in
    arch)   PAQ="$pa" ;;
    deb)    PAQ="$pa_deb" ;;
    fedora) PAQ="$pa_fed" ;;
    *)      PAQ="$pa" ;;
  esac
  faltan=()
  IFS=',' read -ra candidatos <<<"$progs"
  for prog in "${candidatos[@]}"; do
    command -v "$prog" >/dev/null 2>&1 || faltan+=("$prog")
  done
  if [ ${#faltan[@]} -eq 0 ]; then
    ok "$etiqueta  (${progs})"
  else
    FALTAN_PAQ+=("$PAQ")
    aviso "$etiqueta: falta ${faltan[*]} -> paquete $PAQ"
  fi
done

if [ ${#FALTAN_PAQ[@]} -gt 0 ]; then
  echo
  case "$FAMILIA" in
    arch)   echo "  Para instalarlas a mano:  sudo pacman -S ${FALTAN_PAQ[*]}" ;;
    deb)    echo "  Para instalarlas a mano:  sudo apt install ${FALTAN_PAQ[*]}" ;;
    fedora) echo "  Para instalarlas a mano:  sudo dnf install ${FALTAN_PAQ[*]}" ;;
    *)      echo "  No encontre pacman, apt-get ni dnf. Instalas los paquetes a mano:" ;;
  esac
  echo "  dictala arranca igual sin esto, con menos funciones."
  echo
  read -r -p "  ¿Querés que intente instalarlas ahora? [s/N] " r || r="n"
  if [[ "${r,,}" == "s" && "$FAMILIA" != "ninguno" ]]; then
    read -r -p "  Se va a usar sudo. ¿Confirmás? [s/N] " c || c="n"
    if [[ "${c,,}" == "s" ]]; then
      case "$FAMILIA" in
        arch)   sudo pacman -S --needed --noconfirm "${FALTAN_PAQ[@]}" ;;
        deb)    sudo apt-get install -y "${FALTAN_PAQ[@]}" ;;
        fedora) sudo dnf install -y "${FALTAN_PAQ[@]}" ;;
      esac || aviso "La instalacion fallo o se cancelo. Segui manualmente."
    fi
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
    # systemctl puede devolver ok y el daemon morir igual (lo tipico es que no
    # puedas abrir /dev/uinput). Preguntale al daemon, no al gestor de servicios.
    # ydotool solo imprime 'fd_daemon_socket' si logró conectarse: chequeo
    # positivo, no parsing de un error en ingles.
    if ydotool debug 2>&1 | grep -q 'fd_daemon_socket'; then
      aviso "ydotool.service arranco pero ydotoold NO responde."
      echo "    Casi siempre es el grupo 'input':"
      echo "       sudo usermod -aG input \$USER    y volve a iniciar sesion."
      echo "     Texto al portapapeles va a funcionar igual; el pegado automatico no."
    else
      ok "ydotool.service habilitado y ydotoold responde"
    fi
  else
    aviso "No pude habilitar ydotool.service. Probalo vos:"
    echo "     systemctl --user enable --now ydotool.service"
  fi
fi

# --- 6. snippet del compositor --------------------------------------------
# Que compositor corre, no cual esta instalado: tener hyprctl en el PATH no
# significa que estes en Hyprland.
detectar_compositor() {
  if [ -n "${WAYLAND_DISPLAY:-}" ]; then
    if command -v niri >/dev/null 2>&1 && niri msg -j windows >/dev/null 2>&1; then
      echo niri; return
    fi
    if command -v hyprctl >/dev/null 2>&1 && hyprctl -j activewindow >/dev/null 2>&1; then
      echo hyprland; return
    fi
    if command -v swaymsg >/dev/null 2>&1 && swaymsg -t get_tree >/dev/null 2>&1; then
      echo sway; return
    fi
  fi
  if [ -n "${DISPLAY:-}" ] && command -v xdotool >/dev/null 2>&1 &&
     xdotool getactivewindow >/dev/null 2>&1; then
    echo x11; return
  fi
  # Sin sesion grafica (instalacion por SSH, en un contenedor): adivino por la config.
  # El :- importa: el script corre con set -u y esa variable no siempre existe.
  case "${XDG_CURRENT_DESKTOP:-}" in
    *hyprland*) echo hyprland; return ;;
    *sway*)     echo sway; return ;;
    *niri*)     echo niri; return ;;
    *bspwm*)    echo bspwm; return ;;
    *i3*)       echo i3; return ;;
    *gnome*)    echo gnome; return ;;
    *kde*)      echo kde; return ;;
  esac
  for c in niri hypr sway bspwm i3; do
    [ -d "$HOME/.config/$c" ] && { echo "$c"; return; }
  done
  echo desconocido
}

COMP="$(detectar_compositor)"
COMANDO="systemd-run --user --scope -q -p MemoryMax=$MEMORIA $BIN/dictala"

snippet() {
  case "$1" in
    niri)
      cat <<SNIP
    // Dictado por voz.
    // repeat=false: sin esto, mantener la tecla lanza varias transcripciones
    // a la vez y eso puede matar tu sesion (ver README, seccion Importante).
    // systemd-run --scope: saca el proceso del cgroup del compositor y le
    // pone un tope de memoria.
    XF86Calculator repeat=false {
        spawn-sh "$COMANDO"
    }
SNIP
      ;;
    hyprland)
      cat <<SNIP
    # Dictado por voz.
    # El modificador vacio ("," despues de bind) dispara al apretar, no al
    # soltar: sin eso, mantener la tecla lanza varias transcripciones.
    bind = ,XF86Calculator,exec,$COMANDO
SNIP
      ;;
    sway | i3)
      cat <<SNIP
    # Dictado por voz.
    # bindsym dispara al apretar. Con --release dispara al soltar, no es eso.
    bindsym XF86Calculator exec $COMANDO
SNIP
      ;;
    bspwm)
      cat <<SNIP
    # Dictado por voz. En sxhkd la tecla y el comando van en dos lineas:
    # la primera sin sangria, la segunda con cuatro espacios.
    XF86Calculator
        $COMANDO
SNIP
      ;;
    gnome)
      cat <<SNIP
    # Dictado por voz.
    # GNOME sobre Wayland no puede binds de tecla arbitraria. Los atajos
    # globales van por gsettings, en dos pasos:
    #
    # 1) declararlo:
    #    gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "['/org/gnome/settings-daemon/plugins/media-keys/dictala/']"
    #
    # 2) darle la orden:
    #    gsettings set org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:dictala /org/gnome/settings-daemon/plugins/media-keys/dictala/ command "$COMANDO"
    #
    # Ojo: GNOME reserva casi todos los atajos con tecla multimedia, y una
    # combinacion simple suele pisar algo. Si podes, usa una tecla sola.
SNIP
      ;;
    kde)
      cat <<SNIP
    # Dictado por voz.
    # Plasma no tiene una linea de config parecida para atajos globales:
    # en Configuracion del sistema > Teclado > Atajos > Global, anadir un
    # atajo con esta orden:
    $COMANDO
    # En Wayland asignalo a un atajo que no este en uso.
SNIP
      ;;
    *)
      cat <<SNIP
    # Dictado por voz.
    # No pude detectar tu compositor. El comando es el mismo para todos:
    $COMANDO
    # El README tiene el snippet de Hyprland, Sway, i3, bspwm, GNOME, KDE y niri.
SNIP
      ;;
  esac
}

# Tilde a proposito: se imprime para que la copie el usuario, no se expande.
# shellcheck disable=SC2088
case "$COMP" in
  niri)      DESTINO="~/.config/niri/config.kdl, dentro del bloque binds { }" ;;
  hyprland)  DESTINO="~/.config/hypr/hyprland.conf" ;;
  sway)      DESTINO="~/.config/sway/config" ;;
  i3)        DESTINO="~/.config/i3/config" ;;
  bspwm)     DESTINO="~/.config/bspwm/sxhkdrc" ;;
  gnome)     DESTINO="un atajo global de GNOME (ver abajo)" ;;
  kde)       DESTINO="Configuracion del sistema > Teclado > Atajos > Global" ;;
  *)         DESTINO="tu config de compositor (ver README)" ;;
esac

cat <<EOF

$(printf '\033[1;32m')Listo.$(printf '\033[0m')

Para dictalar a mano:
    $BIN/dictala

Diagnostico y calibracion del microfono:
    $BIN/dictala doctor

Pegá esto en $DESTINO:

$(snippet "$COMP")

QUE TECLA ES
    XF86Calculator es la tecla Calculadora, la que dice CALC en muchos
    teclados. Apretala, habla, y el texto aparece donde tengas el cursor.

    Si tu teclado no la tiene, cambiala por la que quieras. Para descubrir
    el nombre de una tecla, corré esto y apretala:

        wev      (niri, Sway, Hyprland -- lo que este en wlroots)
        xev      (X11: bspwm, i3, GNOME, KDE)

    Te imprime el nombre XKB (por ejemplo 'XF86AudioMicMute') y eso es lo
    que va en lugar de XF86Calculator.

El log queda en: \${XDG_RUNTIME_DIR:-/tmp}/dictala.log
EOF