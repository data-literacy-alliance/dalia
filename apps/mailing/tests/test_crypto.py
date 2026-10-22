import secrets

import pytest
from cryptography.fernet import Fernet
from django.test import override_settings
from mailing import crypto
from mailing.exceptions import CredentialDecryptError, EncryptionKeyUnavailable


@pytest.fixture(autouse=True)
def _fresh_cache():
    crypto._reset_cache()
    yield
    crypto._reset_cache()


def use_key_file(tmp_path, content):
    path = tmp_path / "key"
    if content is not None:
        path.write_text(content)
    return override_settings(EMAIL_FERNET_KEY_FILE=str(path))


def test_round_trip_and_trailing_newline(tmp_path):
    with use_key_file(tmp_path, secrets.token_hex(32) + "\n"):
        assert crypto.key_status() == "ok"
        token = crypto.encrypt("s3cret")
        assert token != "s3cret"
        assert crypto.decrypt(token) == "s3cret"


@pytest.mark.parametrize(
    "content,status",
    [
        (secrets.token_hex(32)[:63], "invalid"),
        (secrets.token_hex(32) + "a", "invalid"),
        ("z" * 64, "invalid"),
        (Fernet.generate_key().decode(), "invalid"),
        ("", "missing"),
        ("  \n", "missing"),
        (None, "missing"),
    ],
)
def test_bad_keys_give_none_without_exception(tmp_path, content, status):
    with use_key_file(tmp_path, content):
        assert crypto.get_fernet() is None
        assert crypto.key_status() == status
        with pytest.raises(EncryptionKeyUnavailable):
            crypto.encrypt("x")
        with pytest.raises(EncryptionKeyUnavailable):
            crypto.decrypt("x")


def test_wrong_key_raises_decrypt_error(tmp_path):
    with use_key_file(tmp_path, secrets.token_hex(32)):
        token = crypto.encrypt("value")
    crypto._reset_cache()
    with use_key_file(tmp_path, secrets.token_hex(32)):
        with pytest.raises(CredentialDecryptError):
            crypto.decrypt(token)


def test_garbage_token_raises_decrypt_error(tmp_path):
    with use_key_file(tmp_path, secrets.token_hex(32)):
        with pytest.raises(CredentialDecryptError):
            crypto.decrypt("not-a-token")


def test_key_is_read_once_per_process(tmp_path):
    with use_key_file(tmp_path, secrets.token_hex(32)) as _:
        first = crypto.get_fernet()
        assert crypto.get_fernet() is first


def test_warning_logged_once_with_path_only(tmp_path, caplog):
    with use_key_file(tmp_path, "z" * 64):
        with caplog.at_level("WARNING", logger="mailing.crypto"):
            crypto.key_status()
            crypto.key_status()
    records = [r for r in caplog.records if r.name == "mailing.crypto"]
    assert len(records) == 1
    assert "z" * 64 not in records[0].getMessage()
    assert str(tmp_path / "key") in records[0].getMessage()
