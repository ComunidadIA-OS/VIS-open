"""Acceso con usuario, contraseña y TOTP. Contraseñas y secretos de prueba, solo en memoria."""

import pytest

from dashboard.auth import MAX_FAILURES, add_user, auth_enabled, check_login, totp

PW = "una-contrasena-de-prueba"


def secret_of(tmp_path, user="ana-1"):
    import json

    return json.loads((tmp_path / "usuarios.json").read_text("utf-8"))[user]["totp_secret"]


def test_totp_matches_rfc_6238_vector():
    # RFC 6238, apéndice B (SHA-1): secreto ASCII «12345678901234567890», t = 59 s → 94287082.
    import base64

    secret = base64.b32encode(b"12345678901234567890").decode()
    assert totp(secret, 59)[-6:] == "287082"


def test_login_needs_password_and_code_and_stores_no_plaintext(tmp_path):
    assert not auth_enabled(tmp_path)
    uri = add_user(tmp_path, "ana-1", PW)
    assert auth_enabled(tmp_path) and uri.startswith("otpauth://totp/")
    assert PW not in (tmp_path / "usuarios.json").read_text("utf-8")
    code = totp(secret_of(tmp_path), 1000)
    assert check_login(tmp_path, "ana-1", PW, code, now=1000)[0]
    assert not check_login(tmp_path, "ana-1", "otra-contrasena-larga", code, now=1001)[0]
    assert not check_login(tmp_path, "ana-1", PW, "000000", now=1002)[0]
    assert not check_login(tmp_path, "nadie", PW, code, now=1003)[0]


def test_same_message_for_unknown_user_and_wrong_password(tmp_path):
    add_user(tmp_path, "ana-1", PW)
    a = check_login(tmp_path, "ana-1", "x" * 12, "000000", now=10)[1]
    b = check_login(tmp_path, "nadie", PW, "000000", now=11)[1]
    assert a == b


def test_lockout_after_repeated_failures_then_expires(tmp_path):
    add_user(tmp_path, "ana-1", PW)
    for i in range(MAX_FAILURES):
        check_login(tmp_path, "ana-1", "mala-contrasena!", "000000", now=100 + i)
    good = totp(secret_of(tmp_path), 200)
    ok, why = check_login(tmp_path, "ana-1", PW, good, now=200)
    assert not ok and "15 minutos" in why
    later = 100 + 16 * 60
    assert check_login(tmp_path, "ana-1", PW, totp(secret_of(tmp_path), later), now=later)[0]


def test_weak_password_or_name_like_id_is_refused(tmp_path):
    with pytest.raises(ValueError):
        add_user(tmp_path, "ana-1", "corta")
    with pytest.raises(ValueError):
        add_user(tmp_path, "ana garcia", PW)
    with pytest.raises(ValueError):
        add_user(tmp_path, "ana@correo.es", PW)


def test_app_asks_for_login_when_users_exist_and_hides_sessions(tmp_path, monkeypatch):
    from pathlib import Path

    from streamlit.testing.v1 import AppTest

    add_user(tmp_path, "ana-1", PW)
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    app = Path(__file__).parent.parent / "dashboard" / "app.py"
    at = AppTest.from_file(str(app), default_timeout=60).run()
    assert [t.label for t in at.text_input] == [
        "ID de usuario",
        "Contraseña",
        "Código de 6 cifras del autenticador",
    ]
    assert not any(t.value.startswith("Sesión") for t in at.title)
    at.text_input[0].set_value("ana-1")
    at.text_input[1].set_value(PW)
    at.text_input[2].set_value(totp(secret_of(tmp_path)))
    at.button[0].click().run()
    assert any(t.value.startswith("Sesión") for t in at.title)
