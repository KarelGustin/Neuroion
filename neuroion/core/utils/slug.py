"""
Slug generation for user page_name (e.g. "Karel Gustin" -> "karelgustin").
"""
import re
import unicodedata


def slugify(name: str, max_length: int = 64) -> str:
    """
    Convert a display name to a URL-safe slug (lowercase, no spaces).
    Strips diacritics and keeps only alphanumeric.
    """
    if not name or not name.strip():
        return ""
    # Normalize unicode (e.g. é -> e)
    n = unicodedata.normalize("NFKD", name.strip())
    n = "".join(c for c in n if not unicodedata.combining(c))
    # Lowercase, replace non-alphanumeric with nothing
    slug = re.sub(r"[^a-z0-9]", "", n.lower())
    return slug[:max_length] if slug else "user"
