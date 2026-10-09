from __future__ import annotations

import pytest
import requests
from fakes import FakeResponse, FakeSession, fake_clock

from internet_speed import measurement
from internet_speed.measurement import (
    MeasurementError,
    aggregate,
    download_once,
    measure_speed,
)
from internet_speed.models import RequestSample


def test_download_once_counts_streamed_bytes(monkeypatch):
    response = FakeResponse(
        [b"a" * 1000, b"b" * 1500],
        headers={"Content-Length": "2500"},
    )
    session = FakeSession([response])
    monkeypatch.setattr(measurement.time, "perf_counter", fake_clock([10.0, 10.5]))

    sample = download_once(session, "http://example.com/x", chunk_size=8, timeout=5.0)

    assert sample.index == 1
    assert sample.status_code == 200
    assert sample.bytes_downloaded == 2500
    assert sample.elapsed_seconds == pytest.approx(0.5)
    assert sample.content_length == 2500


def test_download_once_sends_identity_encoding(monkeypatch):
    session = FakeSession([FakeResponse([b"x"])])
    monkeypatch.setattr(measurement.time, "perf_counter", fake_clock([0.0, 0.1]))

    download_once(session, "http://example.com/x")

    assert session.calls[0]["stream"] is True
    assert session.calls[0]["headers"]["Accept-Encoding"] == "identity"


def test_download_once_raises_on_non_2xx(monkeypatch):
    session = FakeSession([FakeResponse([b"x"], status_code=404)])
    monkeypatch.setattr(measurement.time, "perf_counter", fake_clock([0.0, 0.1]))

    with pytest.raises(MeasurementError):
        download_once(session, "http://example.com/missing")


def test_aggregate_computes_averages_and_speed():
    samples = [
        RequestSample(1, 200, 1_000_000, 1.0, 1_000_000),
        RequestSample(2, 200, 2_000_000, 2.0, 2_000_000),
    ]

    result = aggregate(samples)

    assert result.total_bytes == 3_000_000
    assert result.total_seconds == pytest.approx(3.0)
    assert result.average_bytes == pytest.approx(1_500_000)
    assert result.average_seconds == pytest.approx(1.5)
    assert result.bytes_per_second == pytest.approx(1_000_000)
    assert result.megabytes_per_second == pytest.approx(1.0)
    assert result.megabits_per_second == pytest.approx(8.0)
    assert result.warnings == []


def test_aggregate_warns_on_content_length_mismatch():
    samples = [
        RequestSample(1, 200, 100, 0.1, content_length=200),
    ]

    result = aggregate(samples)

    assert len(result.warnings) == 1
    assert "#1" in result.warnings[0]


def test_measure_speed_discards_warmup(monkeypatch):
    session = FakeSession([FakeResponse([b"w" * 10]), FakeResponse([b"m" * 100])])
    monkeypatch.setattr(
        measurement.time,
        "perf_counter",
        fake_clock([0.0, 0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.4]),
    )

    result = measure_speed("http://example.com/x", n=3, warmup=True, session=session)

    assert len(session.calls) == 4
    assert [s.index for s in result.samples] == [1, 2, 3]
    assert all(s.bytes_downloaded == 100 for s in result.samples)


def test_measure_speed_skips_warmup_when_disabled(monkeypatch):
    session = FakeSession([FakeResponse([b"m" * 100])])
    monkeypatch.setattr(
        measurement.time, "perf_counter", fake_clock([0.0, 0.1, 0.1, 0.2])
    )

    result = measure_speed("http://example.com/x", n=2, warmup=False, session=session)

    assert len(session.calls) == 2
    assert len(result.samples) == 2


def test_measure_speed_computes_decimal_units(monkeypatch):
    session = FakeSession([FakeResponse([b"w" * 10]), FakeResponse([b"m" * 500_000])])
    monkeypatch.setattr(
        measurement.time, "perf_counter", fake_clock([0.0, 0.1, 0.1, 0.6])
    )

    result = measure_speed("http://example.com/x", n=1, warmup=True, session=session)

    assert result.total_bytes == 500_000
    assert result.total_seconds == pytest.approx(0.5)
    assert result.megabytes_per_second == pytest.approx(1.0)
    assert result.megabits_per_second == pytest.approx(8.0)


def test_measure_speed_retries_transient_failures():
    session = FakeSession(
        [requests.exceptions.ConnectionError("boom"), FakeResponse([b"x" * 50])]
    )

    result = measure_speed(
        "http://example.com/x",
        n=1,
        warmup=False,
        retries=1,
        session=session,
        sleep=lambda _seconds: None,
    )

    assert len(result.samples) == 1
    assert len(session.calls) == 2


def test_measure_speed_raises_after_retries_exhausted():
    session = FakeSession([requests.exceptions.ConnectionError("boom")])

    with pytest.raises(MeasurementError):
        measure_speed(
            "http://example.com/x",
            n=1,
            warmup=False,
            retries=2,
            session=session,
            sleep=lambda _seconds: None,
        )

    assert len(session.calls) == 3
