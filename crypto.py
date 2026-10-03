import os
import base64
import secrets
import logging
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger("crypto")

KEY_FILE = Path("master.key")
NONCE_SIZE = 12


def _load_or_create_master_key() -> bytes:
    env_key = os.getenv("MASTER_KEY")
    if env_key:
        try:
            key = base64.b64decode(env_key)
            if len(key) != 32:
                raise ValueError("MASTER_KEY must decode to 32 bytes")
            return key
        except Exception as e:
            raise RuntimeError(f"Invalid MASTER_KEY: {e}")

    if KEY_FILE.exists():
        key = KEY_FILE.read_bytes()
        if len(key) != 32:
            raise RuntimeError("master.key is corrupted (not 32 bytes)")
        return key

    key = secrets.token_bytes(32)
    KEY_FILE.write_bytes(key)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass
    log.warning(
        "Generated new master.key. Back it up. Without it, stored tokens "
        "cannot be decrypted."
    )
    return key


_MASTER_KEY = None
_AES = None


def init_crypto():
    global _MASTER_KEY, _AES
    _MASTER_KEY = _load_or_create_master_key()
    _AES = AESGCM(_MASTER_KEY)


def encrypt_token(plaintext: str) -> str:
    nonce = secrets.token_bytes(NONCE_SIZE)
    ct = _AES.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
    return base64.b64encode(nonce + ct).decode("ascii")


def decrypt_token(stored: str) -> str:
    blob = base64.b64decode(stored)
    nonce, ct = blob[:NONCE_SIZE], blob[NONCE_SIZE:]
    return _AES.decrypt(nonce, ct, associated_data=None).decode("utf-8")
