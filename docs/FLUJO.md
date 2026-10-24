# Flujo de VIS Open: de una sesión nueva al panel

Dos diagramas: el **flujo de datos** (qué pasa con cada sesión, paso a paso) y el **organigrama**
(qué parte hace cada cosa y dónde corre). GitHub los dibuja; para las diapositivas se exportan
como imagen desde [mermaid.live](https://mermaid.live).

## 1. Flujo de datos

```mermaid
flowchart TD
    A(["Pleno nuevo publicado<br/>streaming.congreso.es"]) --> B
    A2(["Acto o comisión<br/>enlace copiado por una persona"]) --> B2

    subgraph AUTO1 [Automático · cada semana]
        B["Detectar<br/><code>--buscar</code>"] --> C["Descargar emisión<br/>solo audio original"]
        B2["<code>--congreso-url</code> / <code>--hls-url</code>"] --> C
        C --> D["Escribir fila del manifiesto<br/>licencia_verificada = pendiente"]
    end

    D --> E{"Human in the loop<br/>¿se valida la fila?"}
    E -- "no" --> X(["Descartada"])
    E -- "sí: tipo, tramo, fecha" --> F[/"Una persona lanza<br/><code>--pendientes</code>"/]

    subgraph AUTO2 [Automático · OVH]
        F --> G["Audio · FFmpeg"]
        G --> H["Transcripción · Whisper<br/>GPU"]
        H --> I["Voces · pyannote<br/>GPU"]
        I --> J["Seudonimización<br/>Persona N"]
        J --> K["Género por lenguaje<br/>nunca cara ni voz"]
        K --> L["Bloques de pregunta<br/>reglas"]
        L --> M["M09 y M06 · Qwen<br/>marca preguntas, no cuenta"]
        K --> N["Análisis de vídeo<br/>MediaPipe, sin caras"]
        M --> O["Métricas · pandas<br/>las cifras las calcula el código"]
        N --> O
        O --> P["tiempos.json · coste.json"]
    end

    O --> Q["Panel"]
    Q --> R{"Human in the loop<br/>voces «desconocido»"}
    R -- "2 anotadoras coinciden" --> O
    Q --> S(["Sesión · Evolución con filtros<br/>Resumen · Informe PDF"])
```

## 2. Organigrama: quién hace qué y dónde

```mermaid
flowchart LR
    subgraph PERS [Personas]
        P1["Valida la fila del manifiesto<br/>Excel con desplegables"]
        P2["Lanza <code>--pendientes</code><br/>con los tokens en memoria"]
        P3["Anotadoras: validan<br/>las voces dudosas"]
    end

    subgraph CONG [Congreso · fuente pública]
        C1["streaming.congreso.es<br/>emisiones de plenos"]
        C2["app.congreso.es<br/>página de cada sesión"]
        C3["Datos abiertos<br/>diputadas: medidas A y B"]
    end

    subgraph OVH [OVH · máquina con GPU]
        O1["<code>pipeline.sesion</code><br/>orquesta todos los pasos"]
        O2["Whisper + pyannote<br/>GPU V100S"]
        O3["MediaPipe<br/>CPU"]
        O4["Métricas<br/>pandas"]
        O5["Panel Streamlit<br/>puertos 8501 y 8502"]
        O6[("data/<br/>vídeos, resultados,<br/>manifiesto")]
    end

    subgraph API [API compatible con OpenAI]
        Q1["Qwen3.5-9B<br/>OVH AI Endpoints<br/>o servidor propio"]
    end

    C1 --> O1
    C2 --> O1
    C3 --> O4
    O1 --> O2 --> O6
    O1 --> O3 --> O6
    O1 --> Q1 --> O6
    O6 --> O4 --> O5
    P1 --> O6
    P2 --> O1
    P3 --> O5
    O5 --> U(["Ivette, Veru y quien consulte<br/>«Login with token»"])
```

**Reglas que cumple el flujo:** el género nunca sale de la cara ni de la voz; las cifras las calcula
el código, nunca el modelo; los tokens no se guardan en ficheros; ni audio, ni vídeo, ni
transcripciones reales entran en el repositorio; nada se analiza sin una fila validada por una
persona.
