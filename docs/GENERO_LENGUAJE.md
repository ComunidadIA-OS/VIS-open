# Género por pistas del lenguaje

Estado: **validado por Ivette** el 25 oct 2026 frente a la lista oficial de intervenciones del Congreso (V005–V007): 87 de 87 personas, **83 con género correcto, 0 errores y 4 desconocidas** (las 3 ministras de V006, ya resueltas en la PR #145, y un diputado; detalle en la issue #55). Código en `decision/gender_cues.py`; palabras en `decision/cues/es.toml`.

## Principio

El género de una voz sale del **texto de la transcripción** y siempre con evidencia (frase, minuto, método, confianza). Nunca de la cara, la voz ni el tono. Si no hay pista o se contradicen: `desconocido` y fila en el CSV de revisión.

## Pistas (español)

| Método | Ejemplo sintético | Confianza | A quién se atribuye |
|---|---|---|---|
| `floor_grant` | «Tiene la palabra la señora Pérez» | 0,85 | A la **voz siguiente** (otra distinta de quien da la palabra, dentro de 30 s) |
| `self_role` | «Soy la diputada por Girona», «soy el portavoz» | 0,90 | A quien habla |
| `self_agreement` | «Estoy muy agradecida» | 0,75 | A quien habla |
| `as_role` | «Como diputada, creo…» | 0,60 | A quien habla; **siempre a revisión** (puede ser un tercero) |
| `chair_address` | La Presidencia acaba con un tratamiento a solas: «Señora ministra, cuando quiera.», «Señor presidente del Gobierno.» (sin «gracias», 6 palabras como mucho; «Señora ministra de [ministerio]» se lee hasta «de») | 0,80 | A la **voz siguiente**; solo en intervenciones de la Presidencia |
| `address_edge` | Ese mismo tratamiento, pegado por la diarización al final de la voz anterior o al principio de la siguiente | 0,75 | A quien habla **después** del tratamiento |

En los anuncios, lo que va desde «Grupo» («…del Grupo Parlamentario Popular») no cuenta: el nombre del grupo no dice el género de la persona. Las referencias a terceros («la señora ministra dijo…») no cuentan como pista. Cargos sin forma propia (portavoz, ponente) toman el género del artículo.

## Dar la palabra vale para todos los vídeos

Sesión de control (23 oct 2026, visto bueno de Sabrina, pendiente de Ivette): en las intervenciones de la Presidencia se leen unidos los segmentos seguidos (Whisper parte «Pregunta del | diputado don…»), cuentan también los anuncios («…la formula la diputada doña X», «…del diputado don X») como `floor_grant`, y el tratamiento a solas al final da el género de quien responde (`chair_address`). La Presidencia es la voz que más veces da la palabra o anuncia una pregunta.

Regla de Sabrina: «doy la palabra a la señora / al señor = mujer / hombre»: lo que sigue a «tiene la palabra la señora X» (o «el señor X») es de esa persona. Si la diarización ya separó las voces, se usa la voz siguiente (`floor_grant`, 0,85). Si la dejó fusionada con quien da la palabra, `split_on_floor_grant` (`decision/gender_cues.py`) pasa los eventos siguientes, hasta la próxima vez que se da la palabra, a una voz nueva, siempre que sumen al menos 15 s; después se aplica la misma pista. Límites: unos segundos de la Presidencia justo después de la frase (p. ej. leer el título) pueden quedar en la voz nueva, y un clip que empieza a mitad de una intervención no tiene esa frase y sigue en `desconocido`. Pendiente del visto bueno de Ivette. Efecto medido (20 oct 2026): V001 pasa de 0 % a 98,7 % del tiempo con género (mujer); V002–V004 no cambian.

## Reglas de decisión

1. Sin pistas → `desconocido` + revisión (motivo «sin pistas en el lenguaje»).
2. Pistas de géneros distintos → `desconocido` + revisión («pistas que se contradicen»); la evidencia se conserva.
3. Mejor pista con confianza < 0,7 → `desconocido` + revisión, con la sugerencia en `notes`. Una pista débil (< 0,7) tampoco anula a las fuertes: si hay alguna fuerte, se decide con ellas.
4. En otro caso se asigna el género (`gender_source = pista_lenguaje`) y se guardan las pistas en `Speaker.gender_evidence`.

El CSV de revisión (`ReviewRow`) solo incluye las voces con duda; `gender` queda en blanco para que lo decida la anotadora, y `notes` trae el motivo y hasta 3 pistas con su minuto.

## Uso

```bash
python -m decision.gender_cues data/processed/V001/timeline.json
# → timeline_genero.json y review_genero_anotadora_1.csv en la misma carpeta
```

## Límites conocidos

- Depende de que la diarización asigne bien las voces y de que la transcripción sea buena; una voz mezclada puede recibir una pista ajena (por eso las contradicciones van a revisión).
- No lee todavía «señora presidenta» como pista sobre quien preside, ni liga nombres propios a voces.
- Las confianzas y las listas de palabras son una primera propuesta; Ivette debe validarlas con ejemplos reales anotados.
- Para añadir otro idioma, copia `es.toml` a `<idioma>.toml` y usa `--lang`.

## Cambios en `contracts/` (solo opcionales)

`GenderSource.LANGUAGE_CUE = "pista_lenguaje"` (nuevo valor), clase `GenderEvidence` y `Speaker.gender_evidence` (lista, vacía por defecto). Los ficheros existentes siguen siendo válidos.
