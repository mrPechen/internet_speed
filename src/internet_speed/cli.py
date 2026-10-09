from __future__ import annotations

import argparse
import sys

from .measurement import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    MeasurementError,
    measure_speed,
)
from .models import SpeedResult

DEFAULT_REQUESTS = 10
_SEPARATOR = "-" * 48


def _human_bytes(num_bytes: float) -> str:
    """Форматирует число байт десятичными единицами (по 1000) для вывода."""
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(num_bytes)
    unit_index = 0
    while value >= 1000 and unit_index < len(units) - 1:
        value /= 1000
        unit_index += 1
    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.3f} {units[unit_index]}"


def build_parser() -> argparse.ArgumentParser:
    """Создаёт argparse-парсер с аргументами командной строки утилиты."""
    parser = argparse.ArgumentParser(
        prog="internet-speed",
        description="Measure download throughput against a URL.",
    )
    parser.add_argument("url", help="URL to download, e.g. a large image")
    parser.add_argument(
        "-n",
        "--requests",
        type=int,
        default=DEFAULT_REQUESTS,
        help="number of measured requests (default: %(default)s)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="streaming chunk size in bytes (default: %(default)s)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help="per-request timeout in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--no-warmup",
        action="store_true",
        help="skip the warmup request",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help="retries per failed request (default: %(default)s)",
    )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разбирает ``argv`` и проверяет границы значений; при ошибке завершает
    работу с кодом 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.requests < 1:
        parser.error("--requests must be at least 1")
    if args.chunk_size < 1:
        parser.error("--chunk-size must be at least 1")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.retries < 0:
        parser.error("--retries must be zero or greater")
    return args


def render(
    result: SpeedResult,
    *,
    url: str,
    n: int,
    warmup: bool,
    chunk_size: int,
) -> str:
    """Собирает текстовый отчёт по результату измерения для печати в консоль."""
    warmup_label = "yes" if warmup else "no"
    lines = [
        f"Target: {url}",
        f"Requests: {n} (warmup: {warmup_label}, chunk: {_human_bytes(chunk_size)})",
        "",
        f"{'#':>3}  {'status':>6}  {'bytes':>12}  {'time (s)':>9}  {'MB/s':>9}",
    ]
    for sample in result.samples:
        lines.append(
            f"{sample.index:>3}  {sample.status_code:>6}  "
            f"{_human_bytes(sample.bytes_downloaded):>12}  "
            f"{sample.elapsed_seconds:>9.3f}  "
            f"{sample.megabytes_per_second:>9.3f}"
        )

    lines.extend(
        [
            _SEPARATOR,
            f"Total:            {_human_bytes(result.total_bytes)} "
            f"in {result.total_seconds:.2f} s",
            f"Average request:  {_human_bytes(result.average_bytes)} "
            f"in {result.average_seconds:.2f} s",
            f"Download speed:   {result.megabytes_per_second:.2f} MB/s  "
            f"({result.megabits_per_second:.2f} Mbit/s)",
        ]
    )
    for warning in result.warnings:
        lines.append(f"warning: {warning}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI: разбирает аргументы, запускает измерение и печатает отчёт."""
    args = parse_args(argv)
    try:
        result = measure_speed(
            args.url,
            n=args.requests,
            warmup=not args.no_warmup,
            retries=args.retries,
            chunk_size=args.chunk_size,
            timeout=args.timeout,
        )
    except MeasurementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130

    print(
        render(
            result,
            url=args.url,
            n=args.requests,
            warmup=not args.no_warmup,
            chunk_size=args.chunk_size,
        )
    )
    return 0
