#!/usr/bin/env bash
# Desinstalador de dictala. Idempotente.
# NO toca tu config de niri: si agregaste el bind a mano, queda ahi.

set -euo pipefail

PREFIX="${DICTALA_PREFIX:-$HOME/.local/share/dictala}"
VENV="$PREFIX/venv"
RUTA_CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/dictala/config.toml"

info() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m ok\033[0m %s\n' "$*"; }

info "Parando y deshabilitando ydotool.service (si lo habilitamos)"
if systemctl --user list-unit-files ydotool.service >/dev/null 2>&1; then
  systemctl --user disable --now ydotool.service >/dev/null 2>&1 && \
    ok "ydotool.service deshabilitado" || \
    printf ' !! no pude deshabilitar ydotool.service\n'
fi

info "Borrando el virtualenv: $VENV"
if [ -d "$VENV" ]; then
  rm -rf "$VENV"
  ok "borrado"
else
  ok "no existia"
fi
# El directorio padre solo si quedo vacio.
rmdir "$PREFIX" 2>/dev/null || true

info "Borrando la configuracion: $RUTA_CONFIG"
if [ -f "$RUTA_CONFIG" ]; then
  rm -f "$RUTA_CONFIG"
  rmdir "$(dirname "$RUTA_CONFIG")" 2>/dev/null || true
  ok "borrada"
else
  ok "no existia"
fi

# Los modelos descargados por Hugging Face quedan en la cache: son varios
# cientos de MB. No los borramos solos; si queres:
echo
echo "  Caché de modelos de Whisper (opcional, se borra a mano):"
echo "    ~/.cache/huggingface/hub/models--Systran--faster-whisper-*"
echo
echo "  Tu config de niri NO fue tocado: si agregaste el bind, quitalo vos."
echo "  Busca 'XF86Calculator' en ~/.config/niri/config.kdl"