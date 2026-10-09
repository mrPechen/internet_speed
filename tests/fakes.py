from __future__ import annotations

from typing import Any


class FakeResponse:
    """Поддельный ответ requests с настраиваемыми чанками, статусом и заголовками."""

    def __init__(
        self,
        chunks: list[bytes] | None = None,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Сохраняет тело ответа, код статуса и заголовки для использования в тестах."""
        self._chunks = list(chunks or [])
        self.status_code = status_code
        self.headers = dict(headers or {})

    def iter_content(self, chunk_size: int = 1):
        """Отдаёт заранее заданные чанки тела, игнорируя размер чанка."""
        yield from self._chunks


class FakeSession:
    """Утка-заглушка вместо ``requests.Session``.

    ``responses`` расходуются по порядку; когда остаётся один элемент, он
    переиспользуется — так удобно моделировать warmup и повторяющиеся запросы.
    Элементами могут быть экземпляры ``FakeResponse`` или исключения.
    """

    def __init__(self, responses: list[Any]) -> None:
        """Проверяет, что список ответов не пуст, и инициализирует список вызовов."""
        if not responses:
            raise ValueError("FakeSession needs at least one response")
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        """Записывает вызов и возвращает следующий ответ или поднимает исключение."""
        self.calls.append({"url": url, **kwargs})
        if len(self._responses) > 1:
            item = self._responses.pop(0)
        else:
            item = self._responses[0]
        if isinstance(item, Exception):
            raise item
        return item


def fake_clock(values: list[float]):
    """Возвращает замену ``perf_counter``, отдающую ``values`` по порядку."""
    remaining = list(values)

    def _clock() -> float:
        """Выдаёт следующее значение часов или падает, если значения кончились."""
        if not remaining:
            raise AssertionError("fake clock exhausted")
        return remaining.pop(0)

    return _clock
