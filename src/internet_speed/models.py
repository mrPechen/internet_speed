from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RequestSample:
    index: int
    status_code: int
    bytes_downloaded: int
    elapsed_seconds: float
    content_length: int | None = None

    @property
    def megabytes_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0
        return self.bytes_downloaded / self.elapsed_seconds / 1_000_000


@dataclass(frozen=True)
class SpeedResult:
    samples: list[RequestSample]
    total_bytes: int
    total_seconds: float
    average_bytes: float
    average_seconds: float
    bytes_per_second: float
    megabytes_per_second: float
    megabits_per_second: float
    warnings: list[str] = field(default_factory=list)
