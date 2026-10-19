"""Pipeline de M2: vídeo → audio → transcripción → hablantes → línea de tiempo.

Las dependencias pesadas (faster-whisper, WhisperX, pyannote) se importan dentro
de cada función para que el resto del repo funcione sin ellas.
"""
