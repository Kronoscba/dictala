# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/),
versionado según [SemVer](https://semver.org/lang/es/).

## [No publicado]

## [0.1.0] — sin fecha

Primera versión.

### Agregado

- Dictado de una pulsación: graba, transcribe con faster-whisper en CPU y deja
  el texto en el portapapeles.
- Pegado automático con `ydotool key`, eligiendo `Ctrl+Shift+V` para las
  terminales que estén en la configuración y `Ctrl+V` para el resto.
- Detección de la app enfocada vía el IPC de niri, con caída segura a `Ctrl+V`
  en cualquier otro compositor.
- Carga del modelo en un hilo mientras se graba, para que los ~1.9 s de carga
  queden ocultos detrás de los segundos de silencio.
- Lockfile no bloqueante: una sola transcripción a la vez.
- Corte por silencio configurable y tope de seguridad de grabación.
- Resampleo genérico a 16 kHz con el resampler de FFmpeg vía PyAV, para que
  funcione con cualquier tasa de micrófono y no solo con 48000.
- `dictala doctor`: lista micrófonos con sus tasas, verifica `ydotool` y
  `/dev/uinput`, y mide ruido y voz para sugerir un umbral.
- Configuración por TOML en `~/.config/dictala/config.toml`, con variables
  `DICTALA_*` que la sobrescriben.
- `install.sh` idempotente que no instala nada sin confirmación y no toca la
  configuración del compositor; `uninstall.sh` correspondiente.
- Documentación bilingüe con una tabla honesta de lo probado y lo no probado.

### Notas de diseño

- `blocksize` de 4096 por defecto: con 1024 el dispositivo entrega 47 callbacks
  de Python por segundo y PortAudio reporta `input overflow`.
- `base` es el modelo por defecto. `tiny` es más rápido pero confunde palabras
  en español; `small` es peor que `base`; los modelos grandes son inviables en
  CPU porque Whisper siempre procesa una ventana de 30 segundos.