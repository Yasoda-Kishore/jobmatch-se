"""Split long ad texts into overlapping pieces of words."""


def chunk_text(text: str, max_words: int = 200, overlap: int = 40) -> list[str]:
    """Cut text into chunks of at most max_words words.

    Each chunk repeats the last `overlap` words of the previous one,
    so a sentence cut in half still appears whole in one of the chunks.
    """
    words = text.split()
    if not words:
        return []
    step = max_words - overlap
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + max_words]))
        if start + max_words >= len(words):
            break
    return chunks