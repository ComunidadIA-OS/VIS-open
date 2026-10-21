# Borrador: plan de puesta en producción (RGPD, Reglamento de IA y ética)

> **BORRADOR para Veru** (responsable del plan de producción, 28 oct). Lo ha preparado Sabrina con ayuda de IA a partir de lo que hace el sistema hoy. **No está validado jurídicamente y no sustituye asesoramiento legal.** Las citas de artículos son las habituales y hay que **contrastarlas con el texto oficial** antes de usarlas en la presentación. Lo que está marcado como **DECIDIR** o **VERIFICAR** necesita una persona.

Este plan parte de `docs/RESPONSIBLE_USE.md`, `docs/MODEL_CARD.md`, `docs/DATASET_CARD.md` y `docs/PROVEEDORES.md`. Ayuda con la parte que pide el reto en «ética y normativa».

## 1. Qué hace el sistema y con qué datos (hechos)

| Dato | Qué es | Dónde está | ¿Sale del equipo? | Cuánto tiempo |
|---|---|---|---|---|
| Vídeo y audio de sesiones del Congreso | Actos públicos de cargos públicos, sin alterar, con fuente y fecha | Fuera del repo; unidad compartida del equipo; VM de OVHcloud | Solo a la VM de OVHcloud del equipo | **DECIDIR** |
| Transcripción seudonimizada | Texto con «Persona N» en lugar de nombres | `data/processed/` (no se sube) | Fragmentos a OVH AI Endpoints (M09 y resumen) | **DECIDIR** |
| Etiquetas de género con su evidencia | Frase del lenguaje + minuto; o confirmadas por 2 anotadoras | `data/processed/` | No | **DECIDIR** |
| Respuestas de las anotadoras | Un CSV por anotadora con ID de conexión | `data/processed/` | No | **DECIDIR** |
| Audio de las órdenes de voz | Segundos de la voz de quien usa el panel | No se guarda | Sí: a OVH AI Endpoints para transcribirlo | No se guarda (**VERIFICAR** en OVH) |
| Huellas de voz (embeddings) | Se calculan para separar hablantes dentro de una sesión | Solo durante el análisis | No | No se guardan fuera del proceso (ver `RESPONSIBLE_USE.md`) |

Principios ya aplicados: **sin nombres** (códigos anónimos), **sin reconocimiento facial**, **el género nunca se infiere de la cara ni de la voz**, **todo en local salvo la transcripción de órdenes y Qwen**, **revisión humana** de lo dudoso, resultados **agregados y con margen de error**.

## 2. Roles y responsabilidades

- **Responsable del tratamiento:** **DECIDIR.** En el reto, el equipo; en un despliegue real, la entidad que use la herramienta (una sala de debates, una institución, la propia Comunidad).
- **Encargados / subencargados:** OVHcloud, GitHub, Hugging Face, Google Workspace (ver `docs/PROVEEDORES.md`). **VERIFICAR** que hay contrato de encargado (art. 28 RGPD) con cada uno que reciba datos personales.
- **Delegado de protección de datos:** **DECIDIR** si hace falta según quién despliegue.

## 3. Base jurídica (RGPD): puntos a resolver

La voz y la imagen son datos personales, y los seudonimizados lo siguen siendo. Opciones habituales, a validar:

- **Interés público o interés legítimo** (art. 6.1.e o 6.1.f): personas con cargo público, en actos públicos y retransmitidos; resultados agregados. **VERIFICAR** el aviso legal del Congreso (`docs/FUENTE_CONGRESO.md`) sobre reutilización.
- **Fines de investigación o estadísticos** (art. 89 y garantías): minimización y seudonimización ya aplicadas.
- **Consentimiento** (art. 6.1.a): para salas privadas o personas sin cargo público, con información previa (art. 13) y aviso visible en la sala.

**Voz como dato biométrico (art. 9):** los datos biométricos son categoría especial si se tratan para identificar de forma unívoca a una persona. VIS Open usa embeddings de voz **solo para separar hablantes dentro de una sesión**, sin identificar a nadie. **VERIFICAR** con una persona entendida si eso basta para no considerarlo tratamiento biométrico.

## 4. Evaluación de impacto (EIPD, art. 35): esqueleto

**¿Hace falta?** Probable en producción (tratamiento a escala de voz/imagen con IA). **DECIDIR.** Riesgos a recoger:

| Riesgo | Medidas que ya existen | Pendiente |
|---|---|---|
| Reidentificar a una persona por su voz o su imagen | Sin nombres; códigos «Persona N»; sin reconocimiento facial; tratamiento local | Política de retención y borrado |
| Atribuir mal el género | Solo pistas del lenguaje; `desconocido` visible; dos anotadoras; kappa; «no concluyente» | Medir el error por grupo |
| Sesgos de los modelos de voz y de lenguaje | Revisión humana; margen de error | Medirlos con las sesiones reales (Ivette) |
| Uso para evaluar o vigilar a individuos | Resultados agregados; uso no previsto documentado | Cláusula de uso en el despliegue |
| Filtración de datos reales | Datos fuera del repo; `.env` y claves fuera; acceso con 2FA opcional | Cifrado en reposo, copias, accesos |
| El modelo de lenguaje se equivoca o lo manipula un texto | Salida cerrada con esquema; evidencia literal; texto como dato; sin herramientas | Prueba de inyección sobre texto real |
| Mala interpretación de resultados | Aviso de método siempre visible; cifras por código | Formación de quien lea el informe |

## 5. Reglamento de IA (AI Act): clasificación y obligaciones

**Criterio del proyecto:** ante la duda de si un sistema es de alto riesgo, **se trata como si lo fuera hasta confirmar lo contrario.**

- **Prácticas prohibidas (art. 5):** el sistema **no** reconoce emociones, **no** puntúa socialmente a personas y **no** categoriza biométricamente por atributos sensibles: el género sale del lenguaje, no de la cara ni de la voz. **VERIFICAR** que ninguna función nueva (asistente de voz, validación) se acerque a eso.
- **Alto riesgo (art. 6 y Anexo III):** hoy no se usa para empleo, educación, acceso a servicios ni vigilancia. La categoría a mirar es la de sistemas biométricos (Anexo III, punto 1). **DECIDIR** con asesoramiento si encaja; mientras tanto, tratarlo como posible alto riesgo y cumplir lo razonable: gestión de riesgos, calidad de datos, registro, transparencia, supervisión humana, exactitud y ciberseguridad.
- **Transparencia (art. 50):** quien habla con el asistente debe saber que es una IA, y lo que genera un modelo debe ir marcado. Ya aplicado: el asistente se presenta como IA en su ventana; el resumen del contenido lleva «hecho por IA y con posibles errores».
- **Supervisión humana:** «Human in the loop»: las voces sin género las confirman dos anotadoras; el asistente nunca sugiere el género y no guarda sin «confirmo».
- **Alfabetización en IA (art. 4):** el equipo documenta qué hace cada modelo (`MODEL_CARD.md`); falta una nota breve de formación para quien use el panel.
- **Modelos de terceros:** Whisper y Qwen los publican sus autores; las obligaciones del proveedor del modelo son suyas, las del uso son nuestras.

## 6. Derechos y transparencia

- **Información previa (art. 13):** aviso en la sala donde se grabe; texto tipo en `RESPONSIBLE_USE.md`. **DECIDIR** el texto final.
- **Derechos** (acceso, supresión, oposición): canal y plazo. **DECIDIR.**
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
- [ ] Base jurídica decidida y documentada.
- [ ] EIPD hecha y revisada.
- [ ] Clasificación del Reglamento de IA decidida y documentada.
- [ ] Aviso informativo en la sala y texto de información (art. 13).
- [ ] Política de retención, borrado y copias.
- [ ] Canal para ejercer derechos.
- [ ] Prueba de inyección con texto real y medida del error por grupo.
- [ ] Acceso con usuario y segundo factor activado.
- [ ] Declaración de accesibilidad revisada con personas usuarias (`docs/DECLARACION_ACCESIBILIDAD.md`).
- [ ] Nota de formación para quien lea los informes.
