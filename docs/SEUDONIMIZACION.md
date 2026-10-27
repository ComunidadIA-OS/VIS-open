# Seudonimización

Código: `decision/pseudonymize.py`; se aplica en `pipeline.analyze` antes de asignar el género. Regla del 19 oct: **no se guardan nombres**.

- Cada voz es «Persona N» (N por orden de `speaker_id`); `resumen.json` trae el mapa `speaker_id → Persona N`.
- El nombre que sigue a un tratamiento («la señora X», «me llamo X») se sustituye por el código de la voz siguiente (si quien presidía daba la palabra) o por un código nuevo, estable en todo el vídeo.
- **Modo estricto (por defecto):** cualquier otra palabra con mayúscula a mitad de frase que no esté en la lista `[pseudonymize] keep` de `decision/cues/es.toml` (instituciones, lugares, partidos…) también se sustituye. Prefiere redactar de más que dejar un nombre; si algo útil se redacta, añádelo a la lista.
- La tabla nombre → código vive solo en memoria y no se escribe a disco. El audio original sigue conteniendo las voces: `data/` está fuera de git.
- Reanalizar sin volver a transcribir: `python -m pipeline.reanalyze data/processed/V001`.
- Lugares y ministerios: comunidades y ciudades autónomas, grandes ciudades, países y nombres de
  ministerios se conservan (`[pseudonymize] keep` de `decision/cues/es.toml`, PR #152). No se
  añaden provincias que también son apellidos frecuentes (León, Soria, Toledo…). Solo afecta a las
  transcripciones nuevas: en V005–V007 el texto ya estaba seudonimizado («Persona 30» = Ceuta) y
  el original no se guarda.
- **Límite conocido:** el código se asigna por palabra del nombre, así que dos personas con un
  apellido en común comparten código (en V005, «Persona 7» es un diputado del PP y otro de Vox).
  No afecta a las métricas, que van por voz. Hoja de ruta: códigos por persona.

- **Nombres que la transcripción parte o deja (27 oct, revisión de Ivette):** Whisper corta a veces
  la frase entre dos trozos («doña Ana» | «Ferro, del Grupo…»; «Mire, señor» | «Rojas, …»). Si un
  trozo acaba en un tratamiento o en un código y el siguiente de la misma voz empieza menos de 2 s
  después, su primera palabra se trata como mitad de frase. Una palabra con mayúscula justo detrás
  de un código («Persona 94 Cortés») es el resto del mismo nombre y se quita. La lista de
  excepciones distingue tildes («Cortés» apellido, «Cortes» institución) y, ante dos nombres que
  empiezan en la misma palabra, gana el más largo. Tras «señor/señora/don/doña», una palabra en
  minúscula seguida de signo de puntuación que no es un cargo («señor cuerpo,») también se tapa.
  Reanalizar V005–V007 no cambia ninguna cifra (tiempo por género, muestra y voces iguales).

## Límites

- Un nombre al inicio de frase y solo (una palabra) no se distingue de una palabra normal; un nombre que la transcripción escriba en minúscula no se detecta.
- Dos personas con una palabra en común en su nombre se confunden en un mismo código.
- Revisa siempre las salidas antes de publicarlas.
