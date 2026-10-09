from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestSample:
    """Одна завершённая загрузка: её номер, статус, размер и затраченное время."""

    index: int
    status_code: int
    bytes_downloaded: int
    elapsed_seconds: float
    content_length: int | None = None
    content_type: str | None = None

    @property
    def megabytes_per_second(self) -> float:
        """Пропускная способность одного запроса в десятичных МБ/с.

        Возвращает 0, если время запроса не измерено.
        """
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.bytes_downloaded / self.elapsed_seconds / 1_000_000


@dataclass(frozen=True)
class SpeedResult:
    """Агрегированный результат прогона измерения и записанные предупреждения."""

    samples: list[RequestSample]
    total_bytes: int
    total_seconds: float
    average_bytes: float
    average_seconds: float
    bytes_per_second: float
    megabytes_per_second: float
    megabits_per_second: float
    warnings: list[str] = field(default_factory=list)
