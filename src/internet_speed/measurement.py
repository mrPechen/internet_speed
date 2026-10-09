from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import requests

from .models import RequestSample, SpeedResult

DEFAULT_CHUNK_SIZE = 65_536
DEFAULT_TIMEOUT = 30.0
DEFAULT_RETRIES = 2
RETRY_BACKOFF_SECONDS = 0.5


class MeasurementError(RuntimeError):
    """Raised when a download cannot be completed successfully."""


def _parse_content_length(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def download_once(
    session: Any,
    url: str,
    *,
    index: int = 1,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
) -> RequestSample:
    start = time.perf_counter()
    response = session.get(
        url,
        stream=True,
        timeout=timeout,
        headers={"Accept-Encoding": "identity"},
    )
    status_code = response.status_code
    if not 200 <= status_code < 300:
        raise MeasurementError(f"request #{index} to {url} returned HTTP {status_code}")

    total = 0
    for chunk in response.iter_content(chunk_size=chunk_size):
        if chunk:
            total += len(chunk)
    elapsed = time.perf_counter() - start

    content_length = _parse_content_length(response.headers.get("Content-Length"))
    return RequestSample(
        index=index,
        status_code=status_code,
        bytes_downloaded=total,
        elapsed_seconds=elapsed,
        content_length=content_length,
    )


def aggregate(samples: list[RequestSample]) -> SpeedResult:
    count = len(samples)
    total_bytes = sum(sample.bytes_downloaded for sample in samples)
    total_seconds = sum(sample.elapsed_seconds for sample in samples)

    average_bytes = total_bytes / count if count else 0.0
    average_seconds = total_seconds / count if count else 0.0
    bytes_per_second = total_bytes / total_seconds if total_seconds > 0 else 0.0

    warnings: list[str] = []
    for sample in samples:
        if (
            sample.content_length is not None
            and sample.content_length != sample.bytes_downloaded
        ):
            warnings.append(
                f"request #{sample.index}: Content-Length "
                f"{sample.content_length} != downloaded "
                f"{sample.bytes_downloaded} bytes"
            )

    return SpeedResult(
        samples=list(samples),
        total_bytes=total_bytes,
        total_seconds=total_seconds,
        average_bytes=average_bytes,
        average_seconds=average_seconds,
        bytes_per_second=bytes_per_second,
        megabytes_per_second=bytes_per_second / 1_000_000,
        megabits_per_second=bytes_per_second * 8 / 1_000_000,
        warnings=warnings,
    )


def _download_with_retries(
    session: Any,
    url: str,
    *,
    index: int,
    label: str,
    chunk_size: int,
    timeout: float,
    retries: int,
    sleep: Callable[[float], None],
) -> RequestSample:
    attempts = retries + 1
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            return download_once(
                session,
                url,
                index=index,
                chunk_size=chunk_size,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise MeasurementError(
        f"{label} failed after {attempts} attempt(s): {last_error}"
    ) from last_error


def measure_speed(
    url: str,
    *,
    n: int = 10,
    warmup: bool = True,
    retries: int = DEFAULT_RETRIES,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    timeout: float = DEFAULT_TIMEOUT,
    session: Any | None = None,
    session_factory: Callable[[], Any] = requests.Session,
    sleep: Callable[[float], None] = time.sleep,
) -> SpeedResult:
    owns_session = session is None
    if session is None:
        session = session_factory()

    try:
        if warmup:
            _download_with_retries(
                session,
                url,
                index=0,
                label="warmup request",
                chunk_size=chunk_size,
                timeout=timeout,
                retries=retries,
                sleep=sleep,
            )

        samples = [
            _download_with_retries(
                session,
                url,
                index=i,
                label=f"request #{i}",
                chunk_size=chunk_size,
                timeout=timeout,
                retries=retries,
                sleep=sleep,
            )
            for i in range(1, n + 1)
        ]
    finally:
        if owns_session:
            session.close()

    return aggregate(samples)
