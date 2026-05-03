import requests

from src.rag import embeddings


class FakeResponse:
    def __init__(self, embedding=None, error=False, text=""):
        self._embedding = embedding
        self._error = error
        self.text = text

    def raise_for_status(self):
        if self._error:
            raise requests.HTTPError("500 Server Error")

    def json(self):
        return {"embedding": self._embedding}


def test_get_embedding_retries_with_ascii_fallback(monkeypatch):
    prompts = []

    def fake_post(url, json, timeout):
        prompts.append(json["prompt"])
        if len(prompts) == 1:
            return FakeResponse(error=True, text="unicode prompt rejected")
        return FakeResponse(embedding=[0.1, 0.2, 0.3])

    monkeypatch.setattr(embeddings.requests, "post", fake_post)

    result = embeddings.get_embedding(
        "Yamato Lore / Backstory:\n犯罪組織のボス\nBorn to criminal royalty"
    )

    assert result == [0.1, 0.2, 0.3]
    assert "犯罪" in prompts[0]
    assert "犯罪" not in prompts[1]
    assert "Born to criminal royalty" in prompts[1]


def test_get_embedding_raises_for_empty_text():
    try:
        embeddings.get_embedding("")
    except RuntimeError as e:
        assert "empty text" in str(e)
    else:
        raise AssertionError("Expected empty embedding text to raise")
