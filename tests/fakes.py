from __future__ import annotations

from typing import Any


class FakeResponse:
    def __init__(
        self,
        chunks: list[bytes] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._chunks = list(chunks or [])
        self.status_code = status_code
        self.headers = dict(headers or {})

    def iter_content(self, chunk_size: int = 1):
        yield from self._chunks


class FakeSession:
    """Duck-typed stand-in for ``requests.Session``.

    ``responses`` is consumed in order; when a single item remains it is
    reused, which makes warmup + repeated identical requests easy to model.
    Items may be ``FakeResponse`` instances or exceptions to raise.
    """

    def __init__(self, responses: list[Any]) -> None:
        if not responses:
            raise ValueError("FakeSession needs at least one response")
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"url": url, **kwargs})
        if len(self._responses) > 1:
            item = self._responses.pop(0)
        else:
            item = self._responses[0]
        if isinstance(item, Exception):
            raise item
        return item


def fake_clock(values: list[float]):
    """Return a ``perf_counter`` replacement yielding ``values`` in order."""
    remaining = list(values)

    def _clock() -> float:
        if not remaining:
            raise AssertionError("fake clock exhausted")
        return remaining.pop(0)

    return _clock
