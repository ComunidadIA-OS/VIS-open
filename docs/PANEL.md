# Panel, informe y evolución

Qué hay que construir en la etapa 7 del plan (responsable: Veru). Es **una sola interfaz**: una aplicación web local hecha con Streamlit, que se abre en el navegador y no necesita servidor ni base de datos.

```bash
streamlit run dashboard/app.py
```

## De dónde salen los datos

El panel no calcula nada con IA. Solo lee los ficheros que deja el análisis de cada sesión en `data/processed/<sesión>/`:

- `source.json`: ficha de la sesión (fecha, legislatura, enlace, fuente y huella digital).
- `timeline.json`: línea de tiempo (quién habla, desde qué segundo hasta cuál, y su género con la evidencia).
- `resumen.json` y los resultados de las métricas de `metrics/`.
- Los gestos de mano levantada (tabla de gestos de `contracts/`).

Hasta que existan datos reales, se trabaja con los datos sintéticos de `evaluation/synthetic/muestras/` (`make synthetic`).

## Pantalla 1 · Panel de una sesión

1. **Selector de sesión** (lista de las sesiones procesadas).
2. **Ficha de la sesión**: fecha, legislatura, tipo de sesión, enlace a la fuente y aviso «Fuente: Congreso de los Diputados, vídeo sin alterar».
3. **Cifras principales**, una tarjeta por métrica, separando siempre mujer / hombre / desconocido:
   - M01 Presencia: personas que intervienen, por género.
   - M02 Tiempo de palabra: minutos y porcentaje por género.
   - M03 Turnos: número de intervenciones por género.
   - M04 Brecha de paridad: diferencia en puntos entre el porcentaje de tiempo de mujeres y el de hombres.
   - M13 Sin atribuir: porcentaje de tiempo en que no se sabe quién habla.
   - M14 Peticiones de palabra con la mano, por género.
   - M09 Preguntas recibidas, por género.
   Si una métrica no tiene muestra suficiente, la tarjeta dice «no concluyente» en lugar de la cifra.
4. **Gráfico de barras** del tiempo de palabra por género.
5. **Línea de tiempo** de la sesión: una franja horizontal coloreada según el género de quien habla en cada momento, con las manos levantadas marcadas.
6. **Tabla de intervenciones**: código anónimo de la persona (Persona 1, Persona 2…), minuto de inicio, duración, género y la evidencia del género (la frase y el minuto, con el nombre sustituido por el código, por ejemplo «tiene la palabra la señora [Persona 3]»). Las voces sin pista aparecen como `desconocido`. Nunca se muestran nombres.
7. **Aviso de método**, siempre visible: «El género se asigna solo por pistas del lenguaje de la sesión, nunca por la cara ni la voz. Los resultados son orientativos y requieren revisión humana.»

## Human in the loop: confirmar el género de las voces

Término a usar tal cual en la presentación y el vídeo. En la pantalla de sesión, si el vídeo original está en `data/raw/` (solo en el equipo local), aparece el reproductor y el bloque «Human in the loop». Para cada voz que el lenguaje dejó en `desconocido` se ven sus tramos («Persona 1: de 0:00 a 0:20») con el vídeo en ese punto. Cada anotadora decide mujer, hombre o desconocido y su seguridad; se guarda en `review_anotadora_1.csv` y `review_anotadora_2.csv`. El género solo pasa a las cifras cuando **las dos coinciden** (procedencia `anotacion_percibida`); si no, sigue `desconocido`. El sistema nunca lo decide por la cara ni por la voz: lo decide una persona.

## Informe descargable

Un botón **«Descargar informe»** en la pantalla 1 genera un fichero con el contenido de esa sesión:

- La ficha de la sesión y la fuente.
- Las siete métricas con su valor o «no concluyente».
- El gráfico de tiempo de palabra.
- El método, las limitaciones y el porcentaje sin atribuir.

Formato por defecto: HTML (se abre en cualquier navegador y se puede imprimir a PDF). Un PDF directo queda como evolución futura.

## Pantalla 2 · Evolución entre sesiones

Compara las 3 sesiones de esta entrega, ordenadas por fecha:

- **Gráfico** del porcentaje de tiempo de palabra de las mujeres y de la brecha de paridad (M04) en cada sesión.
- **Tabla resumen**: una fila por sesión con fecha, M01, M02, M03, M04, M13, M14 y M09.
- Aviso: «Con 3 sesiones no se pueden sacar tendencias; el gráfico muestra cómo funcionará con más sesiones.»

## Lo que no debe hacer

- No mostrar caras ni fotogramas del vídeo.
- No hacer clasificaciones de personas concretas (por ejemplo, «quién habla menos»); las cifras se muestran por género.
- No ocultar `desconocido` ni el tiempo sin atribuir.
- No calcular cifras con el modelo de lenguaje: todas salen del código de `metrics/`.

## Cuándo está terminado

- Las dos pantallas y el botón de informe funcionan con los datos sintéticos (20 oct) y con las 3 sesiones reales (27 oct).
- Hay al menos una prueba automática que comprueba que el panel carga una sesión sintética sin errores.
- Funciona en el portátil, sin GPU.
