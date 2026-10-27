# Banco de vídeos de VIS Open: propuesta

> **Estado al 26 oct 2026:** propuesta inicial, conservada como referencia. Lo que se hizo: 3 sesiones de control de evaluación (V005–V007) y la descarga de plenos nuevos con `pipeline.sesion` (`docs/FLUJO.md`, `docs/FUENTE_CONGRESO.md`). MediaPipe no se usa para manos levantadas (M14 descartada), solo para personas visibles.

Fecha: 16 oct 2026 (corregido: la Organización no ofrece vídeos) · Estado: **propuesta, pendiente de aprobación del equipo**

> **ACTUALIZACIÓN (Sabrina, 21 oct 2026): no se usa Google Drive para los vídeos de las sesiones.** Se descargan a mano y se guardan en local y en el espacio del equipo en OVHcloud (`/workspace/equipo6/…/raw`). Drive solo se usa, de momento, para vídeos de trabajo (por ejemplo, un recap) compartidos entre las tres. Las secciones de abajo que hablan del Drive son la propuesta original y **ya no aplican**.

> **DECISIÓN (Sabrina, 16 oct 2026):** el banco se forma solo con **sesiones del Congreso**, y los vídeos **no se modifican ni se alteran**. El fichero original se guarda tal cual (con su `sha256`); el tramo analizado se marca con `tramo_inicio` y `tramo_fin` en el manifiesto, sin cortar ni recodificar el vídeo. El dashboard muestra los resultados aparte, junto al vídeo, sin superponer nada sobre la imagen. Las demás fuentes de la tabla quedan como referencia y no se usan.

> **ALCANCE (Sabrina, 16 oct 2026, decisión "Observatorio MVP"):** VIS Open pasa a ser un observatorio de las mujeres en el Congreso. Incluye una muestra histórica de 6 a 10 plenos comparables (uno por año o por legislatura), una descarga automática de prueba con una sesión nueva y un dashboard de evolución con datos agregados. Procesar todo el archivo queda como hoja de ruta. Hay que preguntar a la Organización si se permite la descarga automática.

## 1. Recomendación en una frase

Montar un banco pequeño (6 a 10 vídeos, 5 a 15 min cada uno) en una **unidad compartida de Google Drive, accesible solo para las tres**, formado por **sesiones públicas de parlamentos** (Congreso y Parlamento Europeo) como núcleo, **1 o 2 vídeos CC BY / CC BY-SA de Wikimedia Commons** para tener formatos de entrevista o mesa redonda, y **1 grabación propia con consentimiento escrito** como "verdad de referencia". Cada vídeo entra solo si tiene su fila completa en el manifiesto CSV. Uso exclusivo de evaluación y demo, **nunca entrenamiento**.

## 2. Fuentes comparadas

Leyenda de riesgo: Bajo / Medio / Alto. "Verificado" significa que se ha leído en la web oficial hoy; "PENDIENTE" significa que no se ha podido comprobar desde aquí y hay que mirarlo a mano.

| # | Fuente | Licencia o condiciones | Riesgo RGPD | Riesgo AI Act | Formatos | Veredicto |
|---|---|---|---|---|---|---|
| 1 | **Congreso de los Diputados**, archivo audiovisual ([web](https://www.congreso.es/archivo-audiovisual)) | Verificado: el [aviso legal](https://www.congreso.es/es/cem/aviso-legal) permite reutilizar la información **si no se altera su contenido, no se desnaturaliza su sentido, se cita la fuente y la fecha de última actualización**. **No** se pueden usar las grabaciones de **interpretación simultánea**. No hay licencia específica para vídeo | Bajo-Medio: cargos públicos en ejercicio de su función, acto público; las opiniones políticas son categoría especial (art. 9 RGPD), pero hechas manifiestamente públicas por la persona (art. 9.2.e) | Bajo con nuestro diseño (sin inferencia automática de sexo ni reconocimiento facial) | Pleno (debate), comisión (comparecencias tipo entrevista) | **Usar (núcleo)** |
| 2 | **Parlamento Europeo**, [Multimedia Centre](https://www.europarl.europa.eu/website/multimedia-centre/en/index.html) | PENDIENTE: la página de condiciones y el aviso legal bloquean la lectura automática. Hay que leer el aviso legal y las condiciones del Multimedia Centre a mano (contacto: avservice@europarl.europa.eu) | Bajo-Medio, igual que el Congreso | Bajo | Pleno, comisiones, ruedas de prensa; varios idiomas (útil para el problema de idioma, pero priorizar español/inglés) | **Usar tras verificar condiciones** |
| 3 | **Wikimedia Commons**, vídeos con CC BY, CC BY-SA o CC0 ([licencias aceptadas](https://commons.wikimedia.org/wiki/Commons:Licensing)) | Licencia por fichero, visible en su página. Obliga a atribuir y, si es BY-SA, a compartir igual lo que derive del vídeo | **Medio**: la licencia cubre derechos de autor, **no** el derecho a la propia imagen ni datos personales ([restricciones no de copyright](https://commons.wikimedia.org/wiki/Commons:Non-copyright_restrictions)). Elegir solo actos públicos (charlas, paneles en conferencias) con personas públicas en esa función | Bajo | Mesas redondas, charlas, entrevistas | **Usar 1-2** para variedad de formato |
| 4 | **Internet Archive** | Sin licencia general: cada ítem tiene sus propios derechos. Solo valen ítems con licencia CC explícita y verificable en el propio ítem | Medio-Alto: procedencia a menudo dudosa (subidas de terceros) | Bajo | Variado | **No usar**, salvo ítem con licencia clara y autoría verificable |
| 5 | **YouTube con "CC BY"** | La licencia del vídeo puede valer, pero descargar va contra las condiciones de servicio de YouTube | Medio | Bajo | Todos | **No usar** (riesgo contractual innecesario) |
| 6 | **TV comercial / RTVE / pódcasts** | Derechos reservados por defecto | Medio | Bajo | Todos | **No usar** |
| 7 | **Grabación propia** (las tres u otras voluntarias simulan un debate o entrevista de 5-10 min) | Nuestra; licencia que decidamos (p. ej. CC BY 4.0 si todas firman) | Bajo **con consentimiento escrito** (art. 6.1.a y art. 7 RGPD; imagen: LO 1/1982). Permite que cada persona **declare** su género, que es el único dato de género que no es atribuido | Bajo | El que diseñemos | **Usar 1** como verdad de referencia (tiempos de palabra exactos, quién levanta la mano) |
| 8 | **Material sintético para tests** (vídeo generado con FFmpeg, tonos o voces TTS de licencia libre) | Nuestro | Ninguno (no hay personas) | Ninguno | Clips de 10-30 s | **Usar** solo para tests automáticos y CI; sí puede ir al repo |

### Reparto recomendado (8 vídeos, por defecto)

| Uso | Vídeos | Fuente |
|---|---|---|
| Evaluación | 2 debates de pleno, 1 comisión | Congreso |
| Evaluación | 1 debate o comisión | Parlamento Europeo (si se verifican condiciones) |
| Evaluación | 1 mesa redonda o entrevista | Wikimedia Commons |
| Evaluación (referencia) | 1 debate simulado con consentimiento | Grabación propia |
| Demo | 1 o 2 de los anteriores, con buen audio y vídeo | Congreso o grabación propia |
| Tests | 2-3 clips cortos | Sintético |

El número final de vídeos de evaluación depende de lo que necesite Ivette para las métricas; queda pendiente.

## 3. Por qué esto cumple con el RGPD y el AI Act

1. **Base legal.** Para sesiones públicas: interés legítimo (art. 6.1.f RGPD) en un análisis estadístico sin ánimo de lucro, sobre personas públicas en función pública. Para la grabación propia: consentimiento (art. 6.1.a). Conviene una breve **evaluación de interés legítimo** (media página) en `docs/`. **Lo debe confirmar la Organización** (ver §7).
2. **Minimización.** Solo el tramo necesario (5-15 min). Las salidas usan `SPEAKER_xx`, no nombres. Los resultados publicados son **agregados** (porcentajes por género atribuido), nunca una ficha de género por persona con nombre.
3. **Género.** Lo ponen **dos anotadoras humanas** como "mujer percibida / hombre percibido / desconocido"; en la grabación propia, el género lo declara cada persona. La IA nunca lo infiere de cara o voz, así que el sistema **no es** un sistema de categorización biométrica (AI Act art. 3.40, prohibiciones del [art. 5.1.g](https://artificialintelligenceact.eu/article/5/) y alto riesgo del [Anexo III.1.b](https://artificialintelligenceact.eu/annex/3/)).
4. **Vídeo sin biometría identificativa.** MediaPipe detecta manos y pose para contar "manos levantadas"; no se calcula ninguna plantilla facial ni se identifica a nadie. Sin reconocimiento de emociones.
5. **Diarización.** pyannote crea embeddings de voz para separar hablantes **dentro de un mismo vídeo**. No se usan para identificar a nadie ni se guardan entre vídeos. Es un punto gris (¿son "datos biométricos" en el sentido del art. 4.14 RGPD?): borrar los embeddings al terminar cada vídeo y **pedir confirmación a la Organización**.
6. **Nunca entrenamiento.** Ningún vídeo ni transcripción se usa para entrenar o ajustar modelos. Consta en el manifiesto (`uso_entrenamiento = no`) y en el DATASET_CARD.
7. **Fuera del repo.** Vídeos, audios, transcripciones y anotaciones con datos personales nunca van a GitHub. Al repo solo va el **esquema** del manifiesto, los clips sintéticos y las métricas agregadas.
8. **Retención.** Propuesta: borrar las copias de trabajo en OVH al terminar cada procesado y el banco completo **30 días después del pitch (4 nov), es decir, el 4 dic 2026**, salvo la grabación propia si las participantes aceptan conservarla. A decidir.

## 4. Organización del Drive

**Unidad compartida** "VIS Open – Banco de vídeos" (no una carpeta en el "Mi unidad" de alguien, para que el material no dependa de una cuenta). PENDIENTE: confirmar que el plan Starter de Sabrina permite unidades compartidas; si no, una carpeta en su Drive compartida solo con las dos compañeras.

```
VIS Open – Banco de vídeos/
├── 00_LEEME.md                    ← reglas de uso (copia corta de esta sección)
├── 01_manifiesto/
│   └── manifiesto.csv             ← fuente de verdad: un vídeo = una fila
├── 02_originales/                 ← solo lectura tras subir; nombre = video_id.ext
│   ├── V001_congreso_pleno.mp4
│   └── ...
├── 03_licencias_y_consentimientos/
│   ├── V001_aviso_legal_captura.pdf   ← captura de la condición vigente el día de descarga
│   └── V007_consentimientos/          ← formularios firmados (acceso solo Sabrina)
├── 04_anotaciones_humanas/        ← CSV de las dos anotadoras, por vídeo
├── 05_salidas_pipeline/           ← timelines y métricas por vídeo (sin vídeo)
└── 99_para_borrar/                ← nada se borra directamente; se mueve aquí y se vacía en la fecha
```

Reglas de acceso:

- Miembros: solo Sabrina, Ivette y Veru. Sabrina como gestora; las otras como "colaborador de contenido". Nadie fuera del equipo.
- Desactivar "compartir con personas externas" y "cualquiera con el enlace".
- La subcarpeta de consentimientos, solo para Sabrina.
- Cuentas con verificación en dos pasos.
- Para procesar en OVH, se copia el vídeo al espacio de transcripción y se borra allí al terminar; el Drive es la única copia permanente.
- PENDIENTE: Google Workspace actúa como encargado del tratamiento (Anexo de tratamiento de datos de Google Cloud/Workspace). Comprobar en la consola de administración que está aceptado. El plan Starter no permite elegir región de datos; se documenta en el plan de producción.

## 5. Manifiesto CSV (una fila por vídeo)

Plantilla: [manifiesto-plantilla.csv](manifiesto-plantilla.csv). Un vídeo **no se analiza** hasta que su fila tenga todos los campos obligatorios y `licencia_verificada = si`.

| Campo | Obligatorio | Contenido |
|---|---|---|
| `video_id` | sí | V001, V002… (también nombre del fichero) |
| `titulo` | sí | Título descriptivo |
| `fuente` | sí | congreso / parlamento_europeo / wikimedia_commons / organizacion / propia / sintetico |
| `url_origen` | sí | Página exacta de donde se descarga |
| `fecha_evento` | sí | AAAA-MM-DD de la sesión o grabación |
| `fecha_descarga` | sí | AAAA-MM-DD |
| `descargado_por` | sí | Nombre de pila de quien lo bajó |
| `licencia` | sí | p. ej. "Aviso legal Congreso", "CC BY-SA 4.0", "Propia, CC BY 4.0" |
| `url_licencia` | sí | Enlace a la licencia o condición |
| `atribucion` | sí | Texto exacto de atribución que hay que mostrar |
| `condiciones` | sí | Restricciones (no alterar, citar fecha, sin interpretación simultánea, share-alike…) |
| `licencia_verificada` | sí | si / pendiente; quién y cuándo en `notas` |
| `formato` | sí | debate / entrevista / mesa_redonda / comparecencia / sintetico |
| `idioma` | sí | es / en / … |
| `tramo_inicio` / `tramo_fin` | sí | hh:mm:ss del fragmento analizado |
| `duracion_s` | sí | Duración del tramo, calculada con ffprobe |
| `personas_publicas` | sí | si / no / mixto |
| `base_legal` | sí | interes_legitimo / consentimiento / no_aplica |
| `ref_consentimiento` | si aplica | Ruta al formulario firmado (sin datos en el CSV) |
| `categorias_especiales` | sí | p. ej. "opiniones políticas, manifiestamente públicas" / ninguna |
| `uso` | sí | evaluacion / demo / test (puede ser "evaluacion;demo") |
| `uso_entrenamiento` | sí | siempre `no` |
| `sha256` | sí | Huella del fichero, para reproducibilidad |
| `ruta_drive` | sí | Ruta dentro de la unidad compartida |
| `fecha_borrado` | sí | Fecha prevista de borrado |
| `anotadoras` | cuando se anote | Iniciales de las dos anotadoras |
| `notas` | no | Lo que no cabe arriba |

El esquema (no el CSV con datos) puede ir al repo como `evaluation/manifest_schema` con un test que valide el CSV.

## 6. Pasos para empezar

1. Sabrina crea la unidad compartida y la plantilla del manifiesto.
2. Veru (datos y ética) revisa las condiciones del Parlamento Europeo y de cada vídeo de Commons y marca `licencia_verificada`.
3. Se eligen tramos del Congreso con al menos una mujer y un hombre interviniendo, y uno con presencia femenina baja, para que la métrica tenga contraste.
4. Se graba el debate simulado con consentimiento escrito (formulario propio, redactado por nosotras).
5. Ivette fija cuántos vídeos de evaluación hacen falta y qué se anota.

## 7. Lo que debería confirmar la Organización

Escribir a comunidad.ia.os@digital.gob.es (o preguntarlo en la formación de Ética) con estas preguntas:

1. ¿Podemos usar sesiones públicas del Congreso y del Parlamento Europeo para el análisis y la demo, y mostrar fragmentos en el vídeo de 5 min y en el pitch? ¿Recortar un tramo o superponer anotaciones cuenta como "alterar el contenido" según el aviso legal del Congreso?
2. ¿Aceptan el interés legítimo como base legal para tratar voz e imagen de cargos públicos en un análisis agregado sin ánimo de lucro?
3. ¿Consideran "datos biométricos" los embeddings de voz de la diarización, si se usan solo dentro de cada vídeo y se borran después?
4. ¿Hay requisitos de dónde guardar los datos (p. ej. solo OVHcloud, o vale Google Drive)?

Esto es una propuesta técnica, no asesoramiento jurídico.

## 8. Qué modelo de Claude conviene para seguir

- Rellenar el manifiesto, calcular `sha256` y `duracion_s` con un pequeño script y el test del esquema: **Claude Code con Sonnet** basta.
- Redactar el formulario de consentimiento, la evaluación de interés legítimo y revisar las respuestas de la Organización: **Opus**, porque pesa el razonamiento jurídico.
- Descargar y subir los vídeos al Drive: a mano, por la persona que los baja (así queda claro quién verificó la licencia).

## Fuentes consultadas (16 oct 2026)

- Aviso legal del Congreso: https://www.congreso.es/es/cem/aviso-legal (verificado)
- Archivo audiovisual del Congreso: https://www.congreso.es/archivo-audiovisual (sin condiciones propias; remite al aviso legal)
- Multimedia Centre del Parlamento Europeo: https://www.europarl.europa.eu/website/multimedia-centre/en/index.html (condiciones PENDIENTES)
- Licencias de Wikimedia Commons: https://commons.wikimedia.org/wiki/Commons:Licensing y https://commons.wikimedia.org/wiki/Commons:Non-copyright_restrictions (no se pudieron leer completas; resumen según la política conocida, verificar a mano)
- AI Act, art. 5: https://artificialintelligenceact.eu/article/5/ ; art. 3: https://artificialintelligenceact.eu/article/3/ ; Anexo III: https://artificialintelligenceact.eu/annex/3/
- Bases del reto: https://github.com/ComunidadIA-OS/Reto-de-Mujeres-por-la-IA-abierta (datos de libre elección; exigen cumplir la normativa de privacidad e IA)

## 9. Hoja de ruta de despliegue (Sabrina, 16 oct 2026)

El producto se diseña para reutilizarse fuera del reto. Para el reto solo se construye el adaptador del Congreso.

| Contexto | Adaptador de fuente | Pista de género | Base legal | Nota |
|---|---|---|---|---|
| Congreso (reto) | Archivo audiovisual del Congreso | "la señora / el señor" de la Presidencia, concordancias | Interés legítimo, cargos públicos | Hay que confirmar si se permite la descarga automática (robots de app.congreso.es) |
| Senado | Web audiovisual del Senado | "la señora senadora / el señor senador" | Igual que el Congreso | Casi idéntico al Congreso |
| Parlamento Europeo y otros parlamentos | Multimedia Centre o equivalente | Fórmulas de tratamiento según idioma (Madame, Frau, etc.) | Igual | Pistas configurables por idioma |
| Universidades | Subida de fichero o plataforma de vídeo | Presentación de ponentes; revisión humana | Interés legítimo o consentimiento | Menos pistas, por lo que hay más revisión |
| Salas de conferencias y reuniones presenciales grabadas | Grabación de la cámara de sala (subida de fichero o carpeta vigilada) | **Declarado** por cada participante en la inscripción; si no, revisión humana | Consentimiento o interés legítimo, con aviso informativo en la sala (art. 13 RGPD); el organizador es el responsable del tratamiento | Aquí el vídeo pesa más (manos levantadas, turnos concedidos) |

Principios comunes: despliegue local en Docker en cada institución, sin enviar vídeos fuera; las mismas métricas en todos los contextos para poder comparar; una plantilla de EIPD y la documentación del AI Act incluidas; nunca inferencia biométrica del género.

### Requisito de producto: avisos (Sabrina, 16 oct 2026)

El producto tiene que avisar, y no solo dejarlo documentado:
- **Plantilla de aviso informativo para la sala** (art. 13 RGPD): se graba, para qué, quién es el responsable del tratamiento, cuánto tiempo se guarda y cómo ejercer los derechos. Se genera desde el propio producto con los datos del organizador.
- **Aviso en cada informe y en el dashboard**: el género es declarado o atribuido por el lenguaje, y la IA nunca lo infiere de la cara o la voz; se muestran el porcentaje de casos "desconocido", los revisados por personas y los límites del método.
- **Aviso al configurar una fuente nueva**: recordar quién es el responsable del tratamiento, la base legal y la EIPD antes de procesar el primer vídeo.
