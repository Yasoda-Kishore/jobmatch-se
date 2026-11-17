"""Functions that clean ad text and guess its language."""
import html
import re

TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
SWEDISH_WORDS = {"och", "att", "vi", "för", "med", "är", "som", "du", "har", "på"}


def clean_text(text: str | None) -> str:
    """Remove HTML tags, decode things like &amp;, and collapse whitespace."""
    if not text:
        return ""
    text = html.unescape(text)
    text = TAG_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def detect_language(text: str) -> str:
    """Return 'sv' if the text looks Swedish, otherwise 'en'."""
    words = re.findall(r"[a-zåäö]+", text.lower())
    if not words:
        return "en"
    swedish = sum(1 for w in words if w in SWEDISH_WORDS)
    return "sv" if swedish / len(words) > 0.03 else "en"