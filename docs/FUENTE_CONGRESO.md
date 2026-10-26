# Fuente: sesiones del Congreso y manifiesto

Decisión del 16 oct 2026: la única fuente del MVP son las sesiones del Congreso **sin modificar**. Código en `sources/`.

## Qué hace

- `VideoSource` (`sources/base.py`) es la interfaz intercambiable de fuentes (RF-19); `CongresoSource` es la única implementada.
- Acepta la URL de una sesión (`app.congreso.es/AudiovisualCongreso/audiovisualdetalledisponible?codOrgano=..&codSesion=..&idLegislaturaElegida=..&fechaSesion=..`) y/o un fichero ya descargado. Solo admite el host `app.congreso.es`.
- Rellena lo que se puede deducir (url, fecha de la sesión, sha256, duración con ffprobe si está instalado) y deja `licencia_verificada=pendiente`. Lo que decide una persona (quién descargó, fecha de descarga, tramo, ruta, fecha de borrado) lo pones tú.
- **No modifica nunca el vídeo**: solo lo lee para calcular la huella.
- La fecha de la URL (`fechaSesion`) se reconoce en `dd/mm/aaaa`, `dd-mm-aaaa` y `aaaa-mm-dd`; si es otra, `fecha_evento` queda vacía y el validador la pide. *El formato real de esa fecha no está comprobado.*

## Uso

```bash
python -m sources.congreso --url "<URL de la sesión>" --file data/raw/V001.mp4 \
  --set descargado_por=Veru --set fecha_descarga=2026-10-17 --set tramo_inicio=00:10:00 \
  --set tramo_fin=00:20:00 --set ruta_drive=02_originales/V001.mp4 --set fecha_borrado=2026-12-04
```

Añade la fila a `data/manifiesto.csv` (o `--manifest`) y lista lo que falta. El vídeo debe llamarse como su `video_id` (`V001.mp4`). Cuando `licencia_verificada` pase a `si` (a mano, tras leer el aviso legal), la fila queda lista.

## El pipeline no analiza sin fila completa

`python -m pipeline.run data/raw/V001.mp4` comprueba antes de nada que existe la fila, que no falta ningún campo obligatorio, que `licencia_verificada=si`, que `uso_entrenamiento=no`, que los formatos son válidos y que el sha256 del fichero coincide con el del manifiesto (por si se hubiera alterado). Si no, se niega y explica qué falta. Con la fila de ejemplo de la plantilla (`EJEMPLO-BORRAR`) también se niega.

## Atribución

Cada ejecución escribe `source.json` junto a la salida con fuente, URL, licencia, sha256 y una `cita` lista para copiar: fuente, fecha de la sesión y fecha de última actualización consultada (usa `fecha_descarga`). *Pendiente de confirmar con Sabrina qué fecha exige exactamente el aviso legal como «fecha de última actualización».*

## Descarga de la emisión (`pipeline.sesion`)

La descarga la hace `pipeline.sesion` (ver [`FLUJO.md`](FLUJO.md)); `CongresoSource.download()` sigue
desactivado (`AUTO_DOWNLOAD=false`) y no se usa.

- **Plenos nuevos, solos:** `python -m pipeline.sesion --buscar` mira si existe en
  `streaming.congreso.es` la emisión del pleno siguiente al último del manifiesto
  (`leg15/400/15_000400_203/cortes/…/manifest.m3u8`), la descarga sin recodificar y escribe su fila
  con `licencia_verificada=pendiente`. Nombre: `<sesión>_pleno_<año>`. Una persona valida la fila
  antes de analizar.
- **Por enlace** (comisiones, actos, plenos antiguos): `--congreso-url` con la página de la sesión
  (la emisión sale de su legislatura, órgano y número) o `--hls-url` con la lista de pistas.
- **Solo el audio original.** La lista de pistas de 2026 trae «Versión original» y «Castellano»
  (la interpretación simultánea, que las condiciones no permiten usar): se coge solo la original, y
  si no la hay, se para. En 2018 y 2022 hay un solo audio dentro del vídeo.
- La descarga se escribe en `<id>.mp4.part` y solo al terminar pasa a `<id>.mp4`, con su sha256.
- **Lo que no se automatiza:** `www.congreso.es` (videoteca, Diario de Sesiones, `robots.txt`)
  responde 403 a los programas, así que el Diario de Sesiones se descarga a mano; además su número
  no coincide con el de la sesión (la sesión 202 de 2026 es el DSCD-15-PL-209). El `robots.txt` de
  `app.congreso.es` redirige a una página de acceso (comprobado el 23 oct 2026).

## Analizar solo un tramo del vídeo

Si el manifiesto trae `tramo_inicio` y `tramo_fin` (hh:mm:ss), el análisis de audio (`pipeline.run`) y el de vídeo (`pipeline.video`) usan **solo ese tramo**, por ejemplo el bloque de preguntas de una sesión de control. El vídeo original no se recorta ni se toca (su huella `sha256` sigue siendo la del original). Los tiempos de todas las salidas son los del vídeo entero, así que el panel y los cortes de «Human in the loop» siguen cuadrando con el original; el tramo deja vacío lo que queda fuera. Sin esos campos se analiza el vídeo completo.
