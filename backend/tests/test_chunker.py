from app.rag.chunker import split_text


def test_short_text_single_chunk():
    assert split_text("hello world", chunk_chars=100, overlap=10) == ["hello world"]


def test_paragraph_packing():
    paras = "\n\n".join(f"paragraph {i} " + "x" * 80 for i in range(10))
    chunks = split_text(paras, chunk_chars=300, overlap=30)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_oversized_paragraph_hard_split():
    text = "y" * 2500
    chunks = split_text(text, chunk_chars=1000, overlap=100)
    assert all(len(c) <= 1000 for c in chunks)
    assert "".join(c[-1] for c in chunks)  # non-empty chunks
    assert len(chunks) >= 3


def test_empty():
    assert split_text("") == []
