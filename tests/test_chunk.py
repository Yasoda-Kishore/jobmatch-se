from jobmatch.ingest.chunk import chunk_text


def test_short_text_gives_one_chunk():
    assert chunk_text("one two three") == ["one two three"]


def test_empty_text_gives_no_chunks():
    assert chunk_text("") == []


def test_long_text_is_split_with_overlap():
    words = [f"w{i}" for i in range(450)]
    chunks = chunk_text(" ".join(words), max_words=200, overlap=40)
    assert len(chunks) == 3
    assert all(len(c.split()) <= 200 for c in chunks)
    # the second chunk starts 40 words before the first one ends
    assert chunks[1].split()[0] == "w160"
    # no words are lost at the end
    assert chunks[-1].split()[-1] == "w449"