# Género por pistas del lenguaje

Estado: **pendiente de validar por Ivette** (reglas y confianzas). Código en `decision/gender_cues.py`; palabras en `decision/cues/es.toml`.

## Principio

El género de una voz sale del **texto de la transcripción** y siempre con evidencia (frase, minuto, método, confianza). Nunca de la cara, la voz ni el tono. Si no hay pista o se contradicen: `desconocido` y fila en el CSV de revisión.

## Pistas (español)

| Método | Ejemplo sintético | Confianza | A quién se atribuye |
|---|---|---|---|
| `floor_grant` | «Tiene la palabra la señora Pérez» | 0,85 | A la **voz siguiente** (otra distinta de quien da la palabra, dentro de 30 s) |
| `self_role` | «Soy la diputada por Girona», «soy el portavoz» | 0,90 | A quien habla |
| `self_agreement` | «Estoy muy agradecida» | 0,75 | A quien habla |
| `as_role` | «Como diputada, creo…» | 0,60 | A quien habla; **siempre a revisión** (puede ser un tercero) |

Las referencias a terceros («la señora ministra dijo…») no cuentan como pista. Cargos sin forma propia (portavoz, ponente) toman el género del artículo.

## Reglas de decisión

1. Sin pistas → `desconocido` + revisión (motivo «sin pistas en el lenguaje»).
2. Pistas de géneros distintos → `desconocido` + revisión («pistas que se contradicen»); la evidencia se conserva.
3. Mejor pista con confianza < 0,7 → `desconocido` + revisión, con la sugerencia en `notes`.
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
