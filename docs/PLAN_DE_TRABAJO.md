# Plan de trabajo de la entrega

Plan del equipo para el reto «Mujeres por la IA Abierta», actualizado el 19 de octubre de 2026. Cada persona dispone de unas 2 horas por día laborable; los fines de semana no se cuentan.

## Fechas clave

| Fecha | Hito |
|---|---|
| 28 oct | Cierre del código y evaluación grupal |
| 30 oct, 08:00 (hora de Madrid) | Entrega oficial: repositorio público con README y presentación .pptx (máximo 20 diapositivas) |
| 4 nov, 08:00 | Entrega del vídeo explicativo de 5 minutos y presentación corta (5 minutos con demo) en el evento |

## Alcance de esta entrega

- 3 sesiones del Congreso de los Diputados, descargadas a mano y guardadas sin modificar.
- Siete métricas: M01 (presencia), M02 (tiempo de palabra), M03 (turnos), M04 (brecha de paridad), M13 (porcentaje sin atribuir), M14 (peticiones de palabra con la mano, a partir del vídeo) y M09 (preguntas recibidas, con IA).
- Panel en Streamlit con el informe de cada sesión y un gráfico de evolución entre sesiones.
- Ajuste ligero del modelo de lenguaje (Qwen) y medición antes y después.
- Lo demás queda en la sección [Evolución futura](#evolución-futura).

## Etapas y tareas

### 1. Preparación

Elegir las sesiones, preparar el almacenamiento y el tablero, dejar listos los accesos de OVH y unir el código.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 19 oct | Ivette | Elegir 3 sesiones del Congreso de años distintos y completar su ficha en el manifiesto: fecha, enlace, legislatura y fuente. | Hoja de cálculo (manifiesto) | — |
| 19 oct | Sabrina | Solicitar la clave de Hugging Face y comprobar el acceso a los espacios de OVH y a AI Endpoints (hecho el 20 oct). El acceso a la organización de GitHub ya está resuelto. **Opcional:** consultar a la Organización la base legal para tratar los datos de las sesiones (preguntas de `docs/BANCO_VIDEOS.md` §7); los formularios de consentimiento solo hacen falta si se graba a personas voluntarias, y la referencia «art. 12.3 de los términos» está por verificar contra el documento original. Las fuentes (aviso legal del Congreso y licencias) se citan en las presentaciones. | Hugging Face, OVHcloud, correo | — |
| 19 oct | Veru | Preparar el almacenamiento de los vídeos (GitHub o, si no es posible, Drive) y un tablero sencillo con las tareas de este plan. | GitHub o Google Drive, GitHub Projects | — |
| 20 oct | Sabrina | Probar el código ya integrado en la GPU de OVH con un vídeo corto y medir tiempo y memoria (docs/PRUEBA_GPU.md). | Docker, espacio 1 de OVH (make smoke) | — |

### 2. Descargar y guardar

Descargar a mano 3 sesiones del Congreso y guardarlas sin modificar, con su ficha y su huella digital.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 20 oct | Veru | Descargar a mano las 3 sesiones, guardarlas sin modificar y calcular su huella digital. Los vídeos no se suben al repositorio público. | Navegador, Python (SHA-256) | manifiesto de Ivette |

### 3. Definir las métricas

Ivette define en una sola tanda las siete métricas de esta entrega. Es la propuesta conceptual de métricas que piden las bases.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 20–21 oct | Ivette | Definir las siete métricas de esta entrega: M01, M02, M03, M04, M13, M14 y M09. | Plantilla de métricas | — |
| 22 oct | Ivette | Revisar 20 ejemplos de la regla de género (pistas del lenguaje, como «la señora» o «el señor»). | Hoja de cálculo | — |

### 4. Transcribir y analizar audio y vídeo

Transcribir, separar a cada persona que habla, asignarle un código anónimo (Persona 1, Persona 2…) y su género por las pistas del lenguaje y detectar las manos levantadas, sin reconocimiento facial.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 21–22 oct | Sabrina | Extraer el audio de las 3 sesiones, transcribirlo y separar a cada persona que habla. El proceso corre solo en OVH; el tiempo es el de prepararlo y revisarlo. | FFmpeg, Whisper (faster-whisper), pyannote, espacio 1 de OVH | sesiones descargadas |
| 23 oct | Sabrina | Asignar a cada voz un código anónimo (Persona 1, Persona 2…) y su género por las pistas del lenguaje; si no hay pista, «desconocido». No se guardan nombres: en la evidencia, el nombre se sustituye por el código. | Python (regla de lenguaje) | transcripción |
| 26 oct | Sabrina | Detectar las manos levantadas en las 3 sesiones, sin reconocimiento facial. | OpenCV, MediaPipe, espacio 1 de OVH | — |

### 5. Programar las métricas

Convertir las definiciones de Ivette en código, con pruebas automáticas.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 21–23 oct | Veru | Programar las métricas M01, M02, M03, M04, M13 y M14 con sus pruebas automáticas. Se empieza con datos de prueba y se pasa a los reales cuando estén. | Python, pandas, pytest | definiciones de Ivette |

### 6. Programar el modelo de lenguaje

Qwen calcula la métrica con IA de esta entrega: preguntas recibidas (M09). Se usa a través de una API compatible con OpenAI, como piden las bases, para poder cambiar de modelo abierto.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 27 oct | Sabrina | Programar la métrica de preguntas recibidas (M09) con Qwen, de forma que el modelo se pueda cambiar por otro modelo abierto. | Qwen vía OVH AI Endpoints (API compatible con OpenAI) | transcripción |

### 7. Panel e informe

Una sola aplicación con los resultados de cada sesión, el informe descargable y un gráfico de evolución entre las 3 sesiones.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 20 oct | Veru | Montar el esqueleto del panel con los datos de prueba del repositorio. | Streamlit | — |
| 26–27 oct | Veru | Completar el panel de cada sesión con los datos reales, el informe descargable y el gráfico de evolución entre las 3 sesiones. | Streamlit | métricas |

### 8. Ajustar el modelo

Ajuste ligero de Qwen en el espacio 2 de OVH con la sesión anotada, una vez listo el panel. Si no mejora, se conserva el modelo sin ajustar y así se indica.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 22–23 oct | Ivette | Anotar a mano 20 minutos de una sesión (qué persona habla, con su código anónimo, y qué preguntas recibe) como referencia para evaluar y ajustar el modelo. Sin nombres. | Hoja de cálculo | — |
| 28 oct | Sabrina | Ajuste ligero del modelo con la anotación de Ivette y medición antes y después. Si no mejora, se conserva el modelo sin ajustar. | Qwen, espacio 2 de OVH (float16) | panel y anotación |

### 9. Evaluación y ética

Comprobar las cifras con la lista de participantes y el Diario de Sesiones, completar el plan de puesta en producción y probar el producto entre las tres.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 26–27 oct | Ivette | Comparar las cifras calculadas con el Diario de Sesiones (número y orden de intervenciones, y género) y anotar los errores para la presentación. Los nombres solo se consultan, no se copian. | Diario de Sesiones, hoja de cálculo | métricas |
| 28 oct | Veru | Completar el plan de puesta en producción (permisos, RGPD y Reglamento de IA) a partir de docs/RESPONSIBLE_USE.md, explicando la seudonimización (Persona 1, Persona 2…) y la minimización de datos. | Documento de texto | — |
| 28 oct | Las tres | Evaluación grupal: las tres prueban el producto de principio a fin y deciden qué se corrige. | Panel e informe | panel e informe |

### 10. Entrega del 30 de octubre

Antes del 30 de octubre a las 08:00 (hora de Madrid): repositorio público con README y presentación .pptx (máximo 20 diapositivas). Si falta algo, el equipo queda fuera de la evaluación.

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 26–29 oct | Ivette | Preparar la presentación .pptx (máximo 20 diapositivas): métricas, datos, aproximación, resultados, demo, plan de puesta en producción, perspectiva de género, marco ético, normativa, riesgos y conclusiones. Sirve también de base para el vídeo del 4 de noviembre. | PowerPoint (.pptx) | validación y plan de producción |
| 29 oct | Veru | Revisar el repositorio antes de publicarlo: que no haya claves ni vídeos, y que el README tenga descripción, instalación y uso, componentes de terceros con sus licencias y hoja de ruta. | GitHub, README | código cerrado el 28 |
| 29 oct | Sabrina | Publicar el repositorio en la organización de GitHub de la Comunidad IA y enviar la presentación antes del 30 de octubre a las 08:00. | GitHub | revisión de Veru y presentación |

### 11. Vídeo y presentación corta del 4 de noviembre

Antes del 4 de noviembre a las 08:00: vídeo explicativo de 5 minutos y versión corta del .pptx para exponer 5 minutos con demo, más el ensayo de las preguntas (3 minutos).

| Cuándo | Quién | Tarea | Herramientas | Depende de |
|---|---|---|---|---|
| 30 oct – 2 nov | Ivette | Preparar la versión corta del .pptx para exponer 5 minutos con demo. | PowerPoint (.pptx) | — |
| 30 oct – 3 nov | Sabrina | Grabar y montar el vídeo explicativo de 5 minutos con la presentación de Ivette y el panel en funcionamiento. Entrega antes del 4 de noviembre a las 08:00. | Grabación de pantalla y editor de vídeo gratuito | presentación de Ivette |
| 2 nov | Veru | Preparar la demo en directo del panel para el evento. | Streamlit | — |
| 3 nov | Las tres | Ensayo de la exposición (5 minutos) y de las preguntas del jurado (3 minutos). | Presentación corta | presentación corta |

## Qué envía cada una y cuándo

Cada envío se hace como muy tarde al final del día indicado. Si un envío se retrasa, quien lo espera trabaja con los datos de prueba del repositorio y avisa al equipo.

| Fecha | Envía | A | Qué | Si se retrasa, afecta a |
|---|---|---|---|---|
| 19 oct | Ivette | Veru | El manifiesto con las 3 sesiones elegidas | Veru no puede descargar, y Sabrina no puede transcribir. Retrasa todo el proyecto. |
| 20 oct | Veru | Sabrina | Las 3 sesiones descargadas, con su huella digital | Sabrina no puede transcribir. Retrasa todas las métricas con datos reales. |
| 21 oct | Ivette | Veru | Las definiciones de las 7 métricas | Veru solo puede preparar el código con datos de prueba; el panel y la validación se retrasan. |
| 21 oct | Ivette | Sabrina | La definición de M09 (preguntas recibidas) | Sabrina no puede programar M09 ni ajustar Qwen. |
| 22 oct | Sabrina | Veru | La transcripción con las voces separadas | Veru sigue con datos de prueba; se retrasan las cifras reales y la validación de Ivette. |
| 22 oct | Ivette | Sabrina | La revisión de los 20 ejemplos de la regla de género | Sabrina asigna el género sin revisión; aumenta el riesgo de errores. |
| 23 oct | Sabrina | Veru | Las voces con su código anónimo y su género | No hay métricas por género; se retrasan el panel y la validación. |
| 23 oct | Ivette | Sabrina | La anotación manual de 20 minutos de una sesión | No se puede evaluar M09 ni ajustar Qwen. |
| 23 oct | Veru | Ivette | Las primeras cifras calculadas | Ivette empieza la revisión más tarde; menos margen para corregir. |
| 26 oct | Sabrina | Veru | Las manos levantadas detectadas en las 3 sesiones | M14 queda sin datos reales; el panel sale sin la parte de vídeo. |
| 27 oct | Sabrina | Veru | Los resultados de M09 | El panel sale sin la métrica con IA. |
| 27 oct | Veru | Ivette | El panel y el informe con datos reales | Ivette no puede validar ni terminar la presentación; Sabrina no puede ajustar Qwen. |
| 27 oct | Ivette | Veru | Los errores detectados en la validación | Quedan errores sin corregir antes del cierre del 28. |
| 28 oct | Veru | Ivette | El plan de puesta en producción | La presentación queda incompleta (es un requisito de las bases). |
| 28 oct | Sabrina | Ivette | El resultado del ajuste de Qwen (antes y después) | La presentación sale sin resultados del ajuste. |
| 29 oct | Veru | Sabrina | El repositorio revisado (claves, vídeos, licencias y README) | Sabrina no puede publicar con seguridad. Riesgo de no cumplir la entrega del 30. |
| 29 oct | Ivette | Sabrina | La presentación .pptx terminada | No se cumple la entrega del 30 (exclusión) y Sabrina no puede grabar el vídeo. |
| 29 oct | Sabrina | La Organización | El repositorio puesto en público en la organización de GitHub de la Comunidad IA, y la presentación .pptx | Exclusión del reto. |
| 2 nov | Veru | Ivette | La demo del panel preparada | La presentación corta va sin demo en directo. |
| 2 nov | Ivette | Las tres | La presentación corta (5 minutos) | No hay ensayo conjunto antes del evento. |
| 3 nov | Sabrina | Las tres | El vídeo montado, para revisarlo el mismo día | Si llega tarde o necesita muchos cambios, no da tiempo a corregirlo antes del 4 a las 08:00. |
| 3 nov | Sabrina | La Organización | El vídeo de 5 minutos, ya revisado (como muy tarde, antes del 4 nov a las 08:00) | Exclusión del reto. |

## Evolución futura

- **Más sesiones:** pasar de 3 a 6–10 sesiones y, después, al archivo del Congreso, el Senado, el Parlamento Europeo, universidades y salas de conferencias.
- **Más métricas:** turno más largo (M05), apertura y cierre (M06), interrupciones (M07), palabra cedida (M08), distribución por cuartil (M10), participación proporcional (M17) y las de vídeo M15, M16 y M19.
- **Más métricas con IA:** roles (M11), temas (M12) y cortes de la Presidencia (M18).
- **Descarga automática:** comprobar el permiso del Congreso y automatizar la descarga.
- **Evaluación ampliada:** métrica de error de segmentación de Albayzin con el corpus Àgora, si su licencia lo permite, y más anotación manual.
- **Documentación:** wiki completa del proyecto y más vistas en el panel.
