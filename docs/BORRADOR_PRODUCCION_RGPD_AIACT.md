# Borrador: plan de puesta en producción (RGPD, Reglamento de IA y ética)

> **BORRADOR para Veru** (responsable del plan de producción, 28 oct). Lo ha preparado Sabrina con ayuda de IA a partir de lo que hace el sistema hoy. **No está validado jurídicamente y no sustituye asesoramiento legal.** Las citas de artículos son las habituales y hay que **contrastarlas con el texto oficial** antes de usarlas en la presentación. Lo que está marcado como **DECIDIR** o **VERIFICAR** necesita una persona.

> **Actualización del 26 oct:** se añaden propuestas para cada punto abierto (marcadas como «Propuesta») y lo ya decidido o medido. Las propuestas no son decisiones hasta que las aprueben Sabrina y Veru.

Este plan parte de `docs/RESPONSIBLE_USE.md`, `docs/MODEL_CARD.md`, `docs/DATASET_CARD.md` y `docs/PROVEEDORES.md`. Ayuda con la parte que pide el reto en «ética y normativa».

## 1. Qué hace el sistema y con qué datos (hechos)

| Dato | Qué es | Dónde está | ¿Sale del equipo? | Cuánto tiempo |
|---|---|---|---|---|
| Vídeo y audio de sesiones del Congreso | Actos públicos de cargos públicos, sin alterar, con fuente y fecha | Fuera del repo; PC de trabajo y espacio del equipo en OVHcloud (no en Drive, decisión del 21 oct) | Solo al espacio de OVHcloud del equipo | Propuesta: en el reto, borrar del PC y de OVHcloud al terminar (después del 4 nov); en producción, al terminar el análisis (el original sigue en la web del Congreso) |
| Transcripción seudonimizada | Texto con «Persona N» en lugar de nombres | `data/processed/` (no se sube) | Fragmentos a OVH AI Endpoints (M09 y resumen) | Propuesta: mientras dure el proyecto y como mucho 12 meses; después, solo las cifras agregadas |
| Etiquetas de género con su evidencia | Frase del lenguaje + minuto; o confirmadas por 2 anotadoras | `data/processed/` | No | Propuesta: igual que la transcripción |
| Respuestas de las anotadoras | Un CSV por anotadora con ID de conexión | `data/processed/` | No | Propuesta: hasta cerrar la validación; después, solo el género acordado (sin el detalle por anotadora) |
| Audio de las órdenes de voz | Segundos de la voz de quien usa el panel | No se guarda | Sí: a OVH AI Endpoints para transcribirlo | No se guarda (**VERIFICAR** en OVH) |
| Huellas de voz (embeddings) | Se calculan para separar hablantes dentro de una sesión | Solo durante el análisis | No | No se guardan fuera del proceso (ver `RESPONSIBLE_USE.md`) |

Principios ya aplicados: **sin nombres** (códigos anónimos), **sin reconocimiento facial**, **el género nunca se infiere de la cara ni de la voz**, **todo en local salvo la transcripción de órdenes y Qwen**, **revisión humana** de lo dudoso, resultados **agregados y con margen de error**.

## 2. Roles y responsabilidades

- **Responsable del tratamiento:** **DECIDIR.** En el reto, el equipo; en un despliegue real, la entidad que use la herramienta (una sala de debates, una institución, la propia Comunidad).
  **Propuesta (26 oct, a aprobar por Sabrina y Veru):** en el reto, el Equipo 6 (Sabrina como directora del proyecto); en producción, la entidad que despliegue VIS Open, que decide qué sesiones se analizan y para qué.
- **Encargados / subencargados:** OVHcloud, GitHub y Hugging Face (ver `docs/PROVEEDORES.md`; Google Workspace y ElevenLabs no forman parte de VIS Open). **VERIFICAR** que hay contrato de encargado (art. 28 RGPD) con cada uno que reciba datos personales.
  Comprobado en las fuentes oficiales el 26 oct 2026 (las condiciones concretas de la cuenta del reto siguen **por verificar**):
  - **OVHcloud**: sí trata datos (vídeos, transcripciones, Qwen). Publica su acuerdo de encargado según el art. 28 RGPD como parte de sus condiciones (versión UE de 23/01/2023, con cláusulas contractuales tipo). En el reto la cuenta es de la Organización.
  - **GitHub**: no recibe datos personales de las sesiones (solo código y datos sintéticos), así que no hace falta. Su acuerdo de protección de datos existe para los planes de pago.
  - **Hugging Face**: solo se descargan modelos y se ejecutan en nuestra máquina; no trata datos, así que no hace falta.
  - **ElevenLabs**: no es proveedor del sistema; solo se usó para la voz del vídeo explicativo, sin datos de las sesiones (`docs/PROVEEDORES.md`).
- **Delegado de protección de datos:** **DECIDIR** si hace falta según quién despliegue.
  **Propuesta (26 oct, a aprobar por Sabrina y Veru):** el equipo no lo necesita (no es un organismo público ni hace observación a gran escala). Una autoridad u organismo público que despliegue VIS Open sí lo necesita (art. 37.1.a RGPD).

## 3. Base jurídica (RGPD): puntos a resolver

**Decidido (Sabrina, 23 oct):** interés legítimo (art. 6.1.f) para las sesiones públicas del Congreso; está así en el manifiesto (`base_legal = interes_legitimo`). Ponderación en breve: el interés es medir la presencia de las mujeres en el debate público; las personas son cargos públicos en sesiones públicas y retransmitidas; se tratan con seudónimos, sin reconocimiento facial y solo en resultados agregados, así que el impacto en sus derechos es bajo. Ojo: una autoridad pública no puede usar el interés legítimo para sus funciones; si la despliega una institución pública, la base sería el interés público (art. 6.1.e).

La voz y la imagen son datos personales, y los seudonimizados lo siguen siendo. Opciones habituales, a validar:

- **Interés público o interés legítimo** (art. 6.1.e o 6.1.f): personas con cargo público, en actos públicos y retransmitidos; resultados agregados. **VERIFICAR** el aviso legal del Congreso (`docs/FUENTE_CONGRESO.md`) sobre reutilización.
- **Fines de investigación o estadísticos** (art. 89 y garantías): minimización y seudonimización ya aplicadas.
- **Consentimiento** (art. 6.1.a): para salas privadas o personas sin cargo público, con información previa (art. 13) y aviso visible en la sala.

**Voz como dato biométrico (art. 9):** los datos biométricos son categoría especial si se tratan para identificar de forma unívoca a una persona. VIS Open usa embeddings de voz **solo para separar hablantes dentro de una sesión**, sin identificar a nadie. **VERIFICAR** con una persona entendida si eso basta para no considerarlo tratamiento biométrico.

## 4. Evaluación de impacto (EIPD, art. 35): esqueleto

**¿Hace falta?** Probable en producción (tratamiento a escala de voz/imagen con IA). **DECIDIR.**
**Propuesta (26 oct, a aprobar por Sabrina y Veru):** hacer la EIPD antes de cualquier puesta en producción, por prudencia: es una tecnología nueva (IA) sobre voz e imagen. En el reto basta con este esqueleto.

Riesgos a recoger:

| Riesgo | Medidas que ya existen | Pendiente |
|---|---|---|
| Reidentificar a una persona por su voz o su imagen | Sin nombres; códigos «Persona N»; sin reconocimiento facial; tratamiento local | Política de retención y borrado |
| Atribuir mal el género | Solo pistas del lenguaje; `desconocido` visible; dos anotadoras; kappa; «no concluyente» | **Medido** frente a la lista oficial (`docs/EVALUACION.md`): 0 errores en mujeres y en hombres; sin género, 0 de 47 mujeres y 1 de 40 hombres |
| Sesgos de los modelos de voz y de lenguaje | Revisión humana; margen de error | Medirlos con las sesiones reales (Ivette) |
| Uso para evaluar o vigilar a individuos | Resultados agregados; uso no previsto documentado | Cláusula de uso en el despliegue |
| Filtración de datos reales | Datos fuera del repo; `.env` y claves fuera; acceso con 2FA opcional | Cifrado en reposo, copias, accesos |
| El modelo de lenguaje se equivoca o lo manipula un texto | Salida cerrada con esquema; evidencia literal; texto como dato; sin herramientas | Prueba de inyección con el modelo real: `python -m evaluation.inyeccion` (resultado en `docs/EVALUACION.md`) |
| Mala interpretación de resultados | Aviso de método siempre visible; cifras por código | Formación de quien lea el informe |

## 5. Reglamento de IA (AI Act): clasificación y obligaciones

**Criterio del proyecto:** ante la duda de si un sistema es de alto riesgo, **se trata como si lo fuera hasta confirmar lo contrario.**

- **Prácticas prohibidas (art. 5):** el sistema **no** reconoce emociones, **no** puntúa socialmente a personas y **no** categoriza biométricamente por atributos sensibles: el género sale del lenguaje, no de la cara ni de la voz. **VERIFICAR** que ninguna función nueva (asistente de voz, validación) se acerque a eso.
- **Alto riesgo (art. 6 y Anexo III):** hoy no se usa para empleo, educación, acceso a servicios ni vigilancia. La categoría a mirar es la de sistemas biométricos (Anexo III, punto 1). **DECIDIR** con asesoramiento si encaja; mientras tanto, tratarlo como posible alto riesgo y cumplir lo razonable: gestión de riesgos, calidad de datos, registro, transparencia, supervisión humana, exactitud y ciberseguridad.
  **Propuesta (26 oct, a aprobar por Sabrina y Veru):** no encaja en los usos del Anexo III: no identifica a nadie (las huellas de voz solo separan hablantes dentro de una sesión) ni categoriza por la voz o la cara. Por el uso sería **riesgo limitado** (obligaciones de transparencia del art. 50). Hasta que lo confirme una persona experta, se mantienen las medidas de alto riesgo que ya aplicamos.
- **Transparencia (art. 50):** quien habla con el asistente debe saber que es una IA, y lo que genera un modelo debe ir marcado. Ya aplicado: el asistente se presenta como IA en su ventana; el resumen del contenido lleva «hecho por IA y con posibles errores».
- **Supervisión humana:** «Human in the loop»: las voces sin género las confirman dos anotadoras; el asistente nunca sugiere el género y no guarda sin «confirmo».
- **Alfabetización en IA (art. 4):** el equipo documenta qué hace cada modelo (`MODEL_CARD.md`); falta una nota breve de formación para quien use el panel.
- **Modelos de terceros:** Whisper y Qwen los publican sus autores; las obligaciones del proveedor del modelo son suyas, las del uso son nuestras.

## 6. Derechos y transparencia

- **Información previa (art. 13):** aviso en la sala donde se grabe; texto tipo en `RESPONSIBLE_USE.md`. **DECIDIR** el texto final.
  - Sesiones del Congreso: los datos no se recogen de las personas (art. 14). Informar a cada diputado sería un esfuerzo desproporcionado (art. 14.5.b), así que la información se publica: README del repositorio y aviso de método en el panel y en los informes.
  - **Propuesta (26 oct, a aprobar por Sabrina y Veru):** texto del aviso en una sala propia: «Esta sesión se graba y se analiza con VIS Open para medir, de forma agregada, la participación por género. No se reconocen caras ni se deduce el género de la voz: se usan las pistas del lenguaje o lo que cada persona declare. Responsable: [entidad]. Puede ejercer sus derechos en [correo]. Más información: [enlace]».
- **Derechos** (acceso, supresión, oposición): canal y plazo. **DECIDIR.**
  **Propuesta (26 oct, a aprobar por Sabrina y Veru):** un correo del responsable publicado en el README y en el aviso; respuesta en un mes (art. 12.3 RGPD). En el reto, el correo del equipo.
- **Decisiones automatizadas (art. 22):** no hay decisiones sobre personas; los resultados son indicadores agregados.

## 7. Seguridad

Ver `SECURITY.md`. En producción: acceso con usuario, contraseña y segundo factor (`dashboard/auth.py`, desactivado por defecto), claves fuera del repo, datos reales fuera de Git, copias de seguridad cifradas, registro de accesos, revisión de proveedores.

## 8. Preguntas abiertas para una consulta legal (opcional)

1. ¿Qué base jurídica es la adecuada para sesiones públicas del Congreso y cuál para una sala privada?
2. ¿Los embeddings de voz usados solo para separar hablantes son tratamiento biométrico?
3. ¿Encaja VIS Open en alguna categoría de alto riesgo del Anexo III?
4. ¿Qué retención es proporcionada para transcripciones seudonimizadas y respuestas de anotadoras?
5. ¿Hace falta delegado de protección de datos y EIPD formal en un despliegue real?
6. ¿Es aceptable que la herramienta de desarrollo con IA vea fragmentos de transcripción seudonimizada en las pruebas, o se debe evitar?

## 9. Lista de comprobación para producción

- [ ] Responsable y encargados identificados; contratos de encargado firmados.
- [x] Base jurídica decidida y documentada (interés legítimo, 23 oct; ver §3).
- [ ] EIPD hecha y revisada.
- [ ] Clasificación del Reglamento de IA decidida y documentada.
- [ ] Aviso informativo en la sala y texto de información (art. 13).
- [ ] Política de retención, borrado y copias.
- [ ] Canal para ejercer derechos.
- [ ] Prueba de inyección con el modelo real (`evaluation/inyeccion.py`) · [x] medida del error por grupo (`docs/EVALUACION.md`).
- [ ] Acceso con usuario y segundo factor activado.
- [ ] Declaración de accesibilidad revisada con personas usuarias (`docs/DECLARACION_ACCESIBILIDAD.md`).
- [ ] Nota de formación para quien lea los informes.
