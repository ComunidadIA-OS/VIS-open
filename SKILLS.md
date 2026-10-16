# SKILLS.md · Procedimientos repetibles del proyecto

Recetas cortas para tareas que se repiten. Cada una dice cuándo usarla, los pasos y qué comprobar. Se pueden convertir en skills de Claude Code más adelante.

## 1. añadir-metrica
Cuándo: Ivette define o cambia una métrica.
1. Escribir la definición en `docs/metricas.md` (ID Mxx, fórmula, umbral, limitaciones, tipo).
2. Crear la función pura en `metrics/` (entrada: DataFrame de eventos; salida: valor + margen).
3. Escribir tests con un caso mínimo hecho a mano y un caso límite (un solo grupo, sin datos).
4. Registrar la métrica en el panel y en la exportación.
5. Comprobar: `make test` en verde; el LLM no interviene en el cálculo.

## 2. verificar-licencia
Cuándo: se añade o cambia cualquier dependencia, modelo o dato.
1. Abrir la fuente oficial (repo o ficha del modelo) y copiar el texto de la licencia.
2. Confirmar que es OSI/FSF y que permite uso comercial; descartar CC BY-NC.
3. Anotar nombre, versión, licencia y URL en `THIRD_PARTY_LICENSES.md`.
4. Para modelos con nombres parecidos (nimble vs nimble-v3) comparar el archivo de licencia de la etiqueta exacta.

## 3. ejecutar-pipeline
Cuándo: procesar un vídeo.
1. Colocar el vídeo en `data/raw/` (ignorado por git).
2. `make pipeline VIDEO=...` → audio, transcripción, hablantes, línea de tiempo.
3. Exportar el CSV de revisión; Veru/Ivette corrigen hablante, género declarado y rol.
4. `make metrics` y abrir el panel con `make dashboard`.
5. Comprobar: porcentaje de tiempo sin atribuir visible; procedencia presente en todos los eventos.

## 4. revisar-genero-y-datos
Cuándo: se incorporan participantes o vídeos nuevos.
1. Registrar la fuente del género (declarado, registro público, anotación de 2 personas).
2. Si hay dudas: `desconocido`. Nunca inferir por cara o voz.
3. Calcular kappa de Cohen entre las dos anotadoras (objetivo ≥0,8).
4. Confirmar que no se sube audio, vídeo ni datos personales al repo.

## 5. benchmark-motor-decision
Cuándo: comparar RulesEngine, Laya, Nimble y Kev (días 8–10, 21–23 oct).
1. Usar los 150 turnos anotados en español (30 ambiguos → `desconocido`).
2. Medir F1 macro, matriz de confusión, calibración, latencia y consistencia al cambiar el orden de opciones.
3. Probar sesgo cambiando nombre o género declarado en el texto.
4. Adoptar un motor solo si gana o queda a 2 puntos de F1 del mejor y es más fácil de ejecutar en local; si ninguno pasa, `RulesEngine` + revisión humana.

## 6. probar-inyeccion-de-prompts
Cuándo: cambia el prompt, el motor o la validación.
1. Ejecutar los 10 turnos maliciosos (órdenes ocultas, intentos de cambiar el formato, texto que simula instrucciones del sistema).
2. Comprobar: salida siempre JSON válido, ninguna instrucción obedecida, casos sospechosos enviados a revisión.

## 7. preparar-entrega
Cuándo: M8 (26–28 oct).
1. Repo público en la organización de la Comunidad IA, licencia OSI, README con licencias de terceros y hoja de ruta.
2. pptx de hasta 20 diapositivas y vídeo de 5 minutos (el mismo en la landing).
3. Landing estática (GitHub Pages) con el vídeo.
4. Escaneo de secretos y revisión de que no hay datos en el repo.
5. Verificar la reproducción con un comando en una máquina limpia.
