# Uso responsable

Esta guía acompaña a la licencia Apache-2.0. **No es una restricción legal añadida a la licencia**: es lo que pedimos a quien use VIS Open y lo que el propio proyecto se compromete a hacer. Complementa la ficha de modelos (`MODEL_CARD.md`) y la ficha de datos (`DATASET_CARD.md`).

## Para qué está hecho

Medir de forma transparente la presencia, la participación y el protagonismo de las mujeres en debates grabados, para que se pueda hablar de ello con datos. Los resultados son indicadores de apoyo, no veredictos.

## Qué te pedimos

- **Con permiso:** usa solo grabaciones que tengas derecho a analizar, con la información y el consentimiento o la base legal que exija la normativa (RGPD y AI Act).
- **Sin identificar a personas:** presenta resultados agregados. No los uses para evaluar, puntuar, vigilar ni sancionar a individuos.
- **Sin reconocimiento facial y sin inferir el género** de nadie a partir de la cara o de la voz. El género sale de pistas del lenguaje (cómo nombra la institución a cada persona), de un dato declarado o de la revisión humana, y el informe dice cómo se obtuvo cada etiqueta.
- **Avisando:** pon un aviso informativo en la sala donde se graba (art. 13 RGPD) y no quites los avisos de método y límites de los informes.
- **Con supervisión humana:** revisa las inferencias marcadas como poco fiables antes de dar un resultado por bueno.
- **Con honestidad sobre los límites:** si la diferencia entre grupos cabe en el margen de error, di "no concluyente". Indica siempre el tamaño de la muestra.
- **Sin datos reales en repositorios públicos:** ni audio, vídeo, transcripciones ni etiquetas de personas.
- **Con credenciales protegidas:** los tokens no se comparten ni se suben.

## Seudonimización y minimización de datos

- **Sin nombres:** VIS Open no guarda nombres. Cada voz se identifica con un código anónimo (Persona 1, Persona 2…). En la evidencia del género y en las transcripciones, el nombre se sustituye por ese código.
- **Solo lo necesario:** se guarda el tiempo de palabra, el turno, el género con su evidencia y los gestos de mano levantada; no se guardan imágenes de caras ni huellas de voz fuera del proceso de análisis.
- **Límite honesto:** seudonimizar reduce el riesgo, pero la voz y la imagen siguen siendo datos personales y, según el RGPD, los datos seudonimizados también lo son. Por eso se mantienen la base legal, los avisos y la supervisión humana.
- **Ajuste del modelo:** el único ajuste previsto (Qwen, para la métrica M09) usa solo texto seudonimizado; el modelo ajustado no se publica.

## Asistente de voz y datos que salen del equipo

- **Qué sale:** solo tu voz diciendo una orden (segundos) hacia la API de transcripción, y fragmentos de **transcripción seudonimizada** hacia el modelo de lenguaje (M09 y resumen). Nunca audio ni vídeo de las sesiones. Detalle y proveedores en `docs/PROVEEDORES.md`.
- **Qué no se guarda:** el audio de las órdenes no se guarda en el equipo. Si el proveedor guarda algo, está por verificar en su documentación.
- **Lista cerrada de órdenes:** el asistente no ejecuta lo que dice una transcripción ni un vídeo; solo encaja la frase en una lista de acciones y nada se guarda sin tu confirmación.
- **Marcado como IA:** el asistente se presenta como IA y lo que genera un modelo (el resumen) lleva «hecho por IA y con posibles errores».
- **Género:** el asistente nunca sugiere el género de una voz; solo registra lo que dice la anotadora.
- **Accesibilidad sin inferir nada de las personas:** no se detecta ni se registra la discapacidad de quien interviene en una sesión (dato de salud). Ver `docs/DECLARACION_ACCESIBILIDAD.md`.

## Usos que no apoyamos

- Vigilancia, seguimiento o identificación de personas.
- Decisiones automatizadas sobre empleo, acceso a servicios, reputación o seguridad de alguien.
- Presentar el género atribuido como un hecho verificado sobre una persona.
- Publicar resultados sin su contexto (muestra, margen de error, método).

## Qué hace el proyecto por su parte

- Documenta modelos, datos y licencias, y reconoce sus límites.
- Mantiene los tests con datos sintéticos y el procesamiento en local.
- Trata como problema de seguridad cualquier dato real o secreto publicado por error (ver `SECURITY.md`).
- Acepta correcciones y avisos de uso indebido por las vías de `CONTRIBUTING.md` y `CODE_OF_CONDUCT.md`.

## Marco

El proyecto se ha diseñado teniendo en cuenta el código ético europeo de la IA y la normativa de protección de datos. El plan de puesta en producción (permisos, RGPD y Reglamento de IA) se completa el 28 de octubre de 2026 y parte de esta guía; hay un **borrador sin validar jurídicamente** en `docs/BORRADOR_PRODUCCION_RGPD_AIACT.md`.
