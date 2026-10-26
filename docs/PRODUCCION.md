# Para producción (fuera de la entrega del reto)

Lo que **no** forma parte de la entrega y se añadiría al pasar a producción. La entrega funciona en local, con ficheros, sin servicios de nube y sin cuentas.

## Acceso y usuarios
- Usuario, contraseña y segundo factor (TOTP) para entrar al panel, con bloqueo tras varios fallos y registro de accesos. Hay un prototipo con la biblioteca estándar de Python en `dashboard/auth.py`, **desactivado por defecto**: solo se activa si existe `data/usuarios.json` (alta con `python -m dashboard.auth add <id>`). La demo y la entrega funcionan sin él.
- ID de conexión guardado en cada revisión, para saber quién confirmó qué y exigir dos personas distintas.
- Si el panel se comparte en una red: detrás de un proxy con HTTPS y con caducidad de sesión.

## Datos compartidos
- Hoy cada anotadora guarda sus revisiones en un CSV local; para que dos personas en equipos distintos coincidan hay que copiar el fichero.
- En producción: una base de datos compartida con usuarios, p. ej. Supabase autoalojado (open source) o PocketBase, detrás de una interfaz pequeña de acceso y guardado para poder cambiar de proveedor. Si hay servicio alojado, se añade a la tabla de subencargados de la política de seguridad.

## Automatización
- **Hecho en la entrega** (`pipeline.sesion`, ver [`FLUJO.md`](FLUJO.md)): detectar los plenos nuevos, descargarlos, escribir su fila del manifiesto, validación humana y análisis completo con `--pendientes` (audio, voces, M09/M06 y vídeo). Probado con el pleno 203 (≈ 74 min, ≈ 2,39 € sin IVA con 1 GPU).
- En OVH, `--buscar` corre en un bucle semanal mientras el notebook está encendido. En producción: `cron` (open source) en una máquina sin GPU para `--buscar`, que no usa tokens; la GPU solo para `--pendientes`, que lanza una persona tras validar (necesita los tokens de Hugging Face y de Qwen, que nunca se guardan en ficheros).
- Pendiente: comprobarlo con el primer pleno que se publique; y hacer el análisis de vídeo en una máquina sin GPU o en paralelo (hoy es la mitad del tiempo de máquina).
- Orquestador: no hace falta uno aparte; si se quisiera, debe ser open source (n8n es «fair-code», no OSI).

## Antes de abrirlo a otras personas
Checklist de la sección 11 de la política de seguridad: MFA, copias de seguridad con restauración probada, HTTPS, secretos fuera del repo, registros, límite de intentos, RGPD y AI Act.
