"""Acceso al panel: usuario, contraseña y segundo factor (TOTP, RFC 6238). Solo biblioteca estándar.

- Los usuarios viven en `data/usuarios.json` (fuera del repo: `data/` está ignorado). Guardan solo
  el hash de la contraseña (scrypt con sal) y el secreto TOTP. Nunca una contraseña en claro.
- Si ese fichero no existe, el panel va en modo abierto (demo sintética o uso local).
- Cinco fallos en 15 minutos bloquean al usuario 15 minutos; todo intento queda en
  `data/auth_log.jsonl` (sin contraseñas ni códigos) para poder auditar.
- Alta: `python -m dashboard.auth add <id>` (pide la contraseña sin mostrarla y enseña una vez el
  secreto del autenticador). También `list` y `remove <id>`.
- shortcut: sin caducidad de sesión ni TLS propio; detrás de red, ponerlo tras un proxy HTTPS.
"""

from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import secrets
import struct
import time
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import quote

MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60
MIN_PASSWORD = 12
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def users_path(data_dir: Path) -> Path:
    return Path(data_dir) / "usuarios.json"


def auth_enabled(data_dir: Path) -> bool:
    return users_path(data_dir).is_file()


def _load(data_dir: Path) -> dict[str, dict[str, str]]:
    path = users_path(data_dir)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _save(data_dir: Path, users: dict[str, dict[str, str]]) -> None:
    path = users_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)


def totp(secret_b32: str, at: float | None = None) -> str:
    """Código de 6 cifras válido durante 30 s (HMAC-SHA1, como Google Authenticator)."""
    counter = int((time.time() if at is None else at) // 30)
    mac = hmac.new(base64.b32decode(secret_b32), struct.pack(">Q", counter), "sha1").digest()
    offset = mac[-1] & 0x0F
    value = (struct.unpack(">I", mac[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def _totp_ok(secret_b32: str, code: str, at: float | None = None) -> bool:
    now = time.time() if at is None else at
    return any(
        hmac.compare_digest(totp(secret_b32, now + drift), code.strip()) for drift in (-30, 0, 30)
    )


def add_user(data_dir: Path, user_id: str, password: str) -> str:
    """Crea o sustituye un usuario y devuelve el URI para el autenticador."""
    if not user_id.replace("-", "").replace("_", "").isalnum() or not 2 <= len(user_id) <= 20:
        raise ValueError(
            "ID no válido: 2 a 20 letras, números, - o _ (nunca un nombre ni un correo)"
        )
    if len(password) < MIN_PASSWORD:
        raise ValueError(f"la contraseña debe tener al menos {MIN_PASSWORD} caracteres")
    salt = secrets.token_bytes(16)
    secret = base64.b32encode(secrets.token_bytes(20)).decode()
    users = _load(data_dir)
    users[user_id] = {
        "salt": salt.hex(),
        "hash": _hash(password, salt).hex(),
        "totp_secret": secret,
    }
    _save(data_dir, users)
    return f"otpauth://totp/VIS%20Open:{quote(user_id)}?secret={secret}&issuer=VIS%20Open"


def _log(data_dir: Path, user_id: str, event: str, now: float) -> None:
    path = Path(data_dir) / "auth_log.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"t": int(now), "id": user_id, "evento": event}) + "\n")


def _recent_failures(data_dir: Path, user_id: str, now: float) -> list[int]:
    path = Path(data_dir) / "auth_log.jsonl"
    if not path.is_file():
        return []
    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    mine = [e for e in events if e["id"] == user_id and now - e["t"] <= LOCK_SECONDS]
    last_ok = max((e["t"] for e in mine if e["evento"] == "ok"), default=0)
    return [e["t"] for e in mine if e["evento"] == "fallo" and e["t"] > last_ok]


def check_login(
    data_dir: Path, user_id: str, password: str, code: str, now: float | None = None
) -> tuple[bool, str]:
    """(entra, motivo). El motivo es el mismo para usuario, contraseña o código erróneos."""
    now = time.time() if now is None else now
    if len(_recent_failures(data_dir, user_id, now)) >= MAX_FAILURES:
        _log(data_dir, user_id, "bloqueado", now)
        return False, "Demasiados intentos. Espera 15 minutos."
    user = _load(data_dir).get(user_id)
    good = False
    if user:
        same = hmac.compare_digest(
            _hash(password, bytes.fromhex(user["salt"])), bytes.fromhex(user["hash"])
        )
        good = same and _totp_ok(user["totp_secret"], code, now)
    else:  # mismo coste de tiempo que un usuario real
        _hash(password, b"\0" * 16)
    _log(data_dir, user_id, "ok" if good else "fallo", now)
    return good, "" if good else "Usuario, contraseña o código incorrectos."


def main(argv: Sequence[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=["add", "list", "remove"])
    ap.add_argument("user_id", nargs="?")
    ap.add_argument("--data", type=Path, default=Path("data"))
    args = ap.parse_args(argv)
    if args.action == "list":
        print("\n".join(sorted(_load(args.data))) or "(sin usuarios)")
    elif not args.user_id:
        ap.error("falta el ID de usuario")
    elif args.action == "remove":
        users = _load(args.data)
        users.pop(args.user_id, None)
        _save(args.data, users)
    else:
        password = getpass.getpass("Contraseña: ")
        if getpass.getpass("Repite la contraseña: ") != password:
            raise SystemExit("Las contraseñas no coinciden.")
        print("Añade esto a tu app de autenticación (una sola vez):")
        print(add_user(args.data, args.user_id, password))


if __name__ == "__main__":
    main()
