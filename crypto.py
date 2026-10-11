"""
Cryptography module for TakeoutRoulette
Implements PBKDF2 (SHA-256, 150,000 iterations) + AES-256-GCM.
Matches the W3C Web Cryptography API (window.crypto.subtle) standards byte-for-byte.
"""
import os
import base64
import json
from pathlib import Path
from typing import Dict, Optional
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from config import BASE_DIR

PBKDF2_ITERATIONS = 150000
KEY_LENGTH_BYTES = 32
SALT_LENGTH_BYTES = 16
IV_LENGTH_BYTES = 12

def encrypt_payload(data_str: str, passphrase: str) -> Dict[str, str]:
    """
    Encrypts a string (JSON database) with AES-256-GCM using a PBKDF2-derived key.
    Returns base64-encoded salt, iv, and ciphertext.
    """
    if not passphrase:
        raise ValueError("Passphrase cannot be empty for encryption.")

    salt = os.urandom(SALT_LENGTH_BYTES)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(passphrase.encode("utf-8"))

    iv = os.urandom(IV_LENGTH_BYTES)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(iv, data_str.encode("utf-8"), None)

    return {
        "salt": base64.b64encode(salt).decode("ascii"),
        "iv": base64.b64encode(iv).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii")
    }

def decrypt_payload(payload: Dict[str, str], passphrase: str) -> str:
    """
    Decrypts an AES-256-GCM payload using PBKDF2 and the passphrase.
    Returns the decoded plaintext UTF-8 string.
    """
    salt = base64.b64decode(payload["salt"])
    iv = base64.b64decode(payload["iv"])
    ciphertext = base64.b64decode(payload["ciphertext"])

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH_BYTES,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
    )
    key = kdf.derive(passphrase.encode("utf-8"))
    aesgcm = AESGCM(key)
    plaintext_bytes = aesgcm.decrypt(iv, ciphertext, None)
    return plaintext_bytes.decode("utf-8")

def load_passphrase_from_env() -> Optional[str]:
    """
    Checks TAKEOUT_PASSPHRASE in environment variables or a local .env file.
    """
    if "TAKEOUT_PASSPHRASE" in os.environ and os.environ["TAKEOUT_PASSPHRASE"].strip():
        return os.environ["TAKEOUT_PASSPHRASE"].strip()

    env_file = BASE_DIR / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    if key.strip() in ("TAKEOUT_PASSPHRASE", "WGC_PASSPHRASE"):
                        clean_val = val.strip().strip("'\"")
                        if clean_val:
                            return clean_val
        except Exception:
            pass

    return None
