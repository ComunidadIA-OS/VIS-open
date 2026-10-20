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
- Detectar sesiones nuevas, descargarlas a un almacenamiento propio, analizarlas en la GPU y dejar a las anotadoras solo las voces `desconocido`.
- Bloqueos por resolver: la regla de ejecutar todo en local, el permiso de descarga automática del Congreso (sin confirmar) y qué ejecuta el análisis en la GPU (el notebook de OVH es interactivo; haría falta un job o una VM).
- Orquestador: debe ser open source. n8n es «fair-code» (no OSI); alternativas a verificar en su fuente antes de citarlas: Node-RED, Activepieces, o un `cron` con un script.

## Antes de abrirlo a otras personas
Checklist de la sección 11 de la política de seguridad: MFA, copias de seguridad con restauración probada, HTTPS, secretos fuera del repo, registros, límite de intentos, RGPD y AI Act.
