from __future__ import annotations

import pytest

from internet_speed import cli
from internet_speed.measurement import MeasurementError
from internet_speed.models import RequestSample, SpeedResult


def make_result() -> SpeedResult:
    return SpeedResult(
        samples=[RequestSample(1, 200, 1_000_000, 0.5, 1_000_000)],
        total_bytes=1_000_000,
        total_seconds=0.5,
        average_bytes=1_000_000,
        average_seconds=0.5,
        bytes_per_second=2_000_000,
        megabytes_per_second=2.0,
        megabits_per_second=16.0,
        warnings=[],
    )


def test_parse_args_defaults():
    args = cli.parse_args(["http://example.com/big.jpg"])

    assert args.url == "http://example.com/big.jpg"
    assert args.requests == 10
    assert args.chunk_size == 65536
    assert args.timeout == 30.0
    assert args.no_warmup is False
    assert args.retries == 2


def test_parse_args_overrides():
    args = cli.parse_args(
        [
            "http://example.com/big.jpg",
            "-n",
            "3",
            "--no-warmup",
            "--retries",
            "0",
            "--timeout",
            "5",
            "--chunk-size",
            "1024",
        ]
    )

    assert args.requests == 3
    assert args.no_warmup is True
    assert args.retries == 0
    assert args.timeout == 5.0
    assert args.chunk_size == 1024


def test_parse_args_requires_url():
    with pytest.raises(SystemExit):
        cli.parse_args([])


def test_render_contains_summary():
    text = cli.render(
        make_result(),
        url="http://example.com/big.jpg",
        n=1,
        warmup=True,
        chunk_size=65536,
    )

    assert "Target: http://example.com/big.jpg" in text
    assert "Download speed" in text
    assert "2.00 MB/s" in text
    assert "Mbit/s" in text


def test_main_success(monkeypatch, capsys):
    monkeypatch.setattr(cli, "measure_speed", lambda *a, **k: make_result())

    code = cli.main(["http://example.com/big.jpg"])

    out = capsys.readouterr().out
    assert code == 0
    assert "Download speed" in out


def test_main_measurement_error(monkeypatch, capsys):
    def boom(*args, **kwargs):
        raise MeasurementError("connection refused")

    monkeypatch.setattr(cli, "measure_speed", boom)

    code = cli.main(["http://example.com/big.jpg"])

    err = capsys.readouterr().err
    assert code == 1
    assert "connection refused" in err
