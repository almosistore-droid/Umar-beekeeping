"""Password hashing with scrypt (Python standard library): salted, slow on purpose, constant-time check."""
import base64
import hashlib
import hmac
import secrets

N, R, P = 2**14, 8, 1  # ~16 MB of memory per hash: fine for a server, expensive for guessing
_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/o, 1/l/i: a temporary password is read aloud or retyped


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=32)
    return f"scrypt${N}${R}${P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored:
        # same work as a real check, so a missing account cannot be told apart by timing
        hashlib.scrypt(password.encode(), salt=b"0" * 16, n=N, r=R, p=P, dklen=32)
        return False
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(base64.b64decode(digest)))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, base64.b64decode(digest))


def temporary_password() -> str:
    """e.g. «k7mq-3vxe-p9ta»: given by the admin, changed by the person at the first login."""
    return "-".join("".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(3))
