"""
Passcode hashing and verification (4-6 digit passcodes for personal dashboard).
"""
from passlib.context import CryptContext

_passcode_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=10)


def hash_passcode(passcode: str) -> str:
    """Hash a passcode for storage. Expects 4-6 digit string."""
    return _passcode_ctx.hash(passcode)


def verify_passcode(passcode: str, hashed: str) -> bool:
    """Verify a passcode against stored hash."""
    if not hashed:
        return False
    try:
        return _passcode_ctx.verify(passcode, hashed)
    except Exception:
        return False


def is_valid_passcode_format(passcode: str) -> bool:
    """Passcode must be 4-6 digits."""
    if not passcode or not isinstance(passcode, str):
        return False
    return len(passcode) >= 4 and len(passcode) <= 6 and passcode.isdigit()
