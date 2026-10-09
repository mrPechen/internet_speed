# internet-speed — design

## Goal

A small console utility that measures download throughput against a given URL.
It accepts an address, performs a fixed number of sequential HTTP requests,
waits for each response, and prints per-request stats plus the average request
time, the total downloaded volume, and the resulting speed in MB/s.

## Non-goals

- No upload / latency / jitter measurement.
- No parallel streams (the measurement is strictly sequential by design).
- No server selection or multi-node testing like a full speedtest client.

## Measurement methodology

The approach follows the hygiene used by common speedtest tools:

- A **warmup** request is issued first and discarded. It resolves DNS and
  establishes the TCP/TLS connection and a keep-alive connection pool, so the
  measured requests reflect transfer throughput rather than connection setup.
- Requests reuse a single `requests.Session`, so subsequent requests reuse the
  established connection.
- `Accept-Encoding: identity` is sent so the byte count reflects bytes actually
  transferred over the wire rather than decompressed bytes.
- Response bodies are streamed in chunks and counted with `len(chunk)`; the
  whole request/response cycle is timed with a single `time.perf_counter()`
  span.
- Speed is computed as a time-weighted throughput:
  `bytes_per_second = total_bytes / total_seconds`.
- Units are decimal (as in speedtest): `MB/s = bytes_per_second / 1_000_000`
  and `Mbit/s = bytes_per_second * 8 / 1_000_000`.
- Response status is validated (2xx required) and `Content-Length`, when
  present, is compared against the downloaded byte count; a mismatch is
  reported as a warning.
- `Content-Type` is inspected: when the URL serves an HTML page rather than a
  downloadable file, the run still reports numbers but adds a warning that the
  measurement is not meaningful.

## Architecture

```
src/internet_speed/
├── __init__.py        # package version and public exports
├── __main__.py        # `python -m internet_speed` entrypoint
├── models.py          # RequestSample, SpeedResult dataclasses
├── measurement.py     # download_once, measure_speed, aggregation
└── cli.py             # argparse, validation, console rendering
```

The core (`measurement.py`) is decoupled from the CLI and from the concrete
`requests.Session`: it accepts any duck-typed session object exposing
`get(url, stream=..., timeout=...)`. This keeps the logic unit-testable without
network access.

### Data flow

```
cli.main(argv)
  -> parse args / validate
  -> measurement.measure_speed(session, url, n, warmup, retries, ...)
       -> optional warmup request (discarded)
       -> n x download_once(...) -> RequestSample
       -> aggregate(samples) -> SpeedResult
  -> cli.render(result) -> stdout
```

## Core API

- `download_once(session, url, chunk_size, timeout) -> RequestSample`
- `measure_speed(url, n=10, warmup=True, retries=0, chunk_size=65536,
   timeout=30.0, session_factory=requests.Session,
   sleep=time.sleep) -> SpeedResult`
- `aggregate(samples) -> SpeedResult`
- `RequestSample(index, status_code, bytes_downloaded, elapsed_seconds,
   content_length, content_type)`
- `SpeedResult(samples, total_bytes, total_seconds, average_bytes,
   average_seconds, bytes_per_second, megabytes_per_second,
   megabits_per_second, warnings)`

## Retries

A request that fails with a network error or timeout is retried up to
`--retries` times with a short linear backoff. Non-2xx status codes are not
retried (they are a server response, not a transport failure). If retries are
exhausted, `measure_speed` raises `MeasurementError` with a clear message.

## CLI

```
python -m internet_speed <URL> [-n 10] [--chunk-size 65536] [--timeout 30]
                              [--no-warmup] [--retries 2]
```

- `URL` — required positional address to measure.
- `-n/--requests` — number of measured requests (default 10).
- `--chunk-size` — streaming chunk size in bytes (default 65536).
- `--timeout` — per-request timeout in seconds (default 30).
- `--no-warmup` — skip the warmup request.
- `--retries` — retries per failed request (default 2).

Exit codes: `0` success, `2` argument error, `1` measurement failure.

### Output

```
Target: https://example.com/heavy.jpg
Requests: 10 (warmup: yes, chunk: 65.536 KB)

 #   status   bytes      time (s)   MB/s
 1   200      1.234 MB   0.412      2.995
 ...
-----------------------------------------------
Total:            12.34 MB in 4.12 s
Average request:  1.234 MB in 0.412 s
Download speed:  2.99 MB/s  (23.95 Mbit/s)
```

## Testing

All tests run without network access using a fake session object with a
controllable `iter_content` and `headers`. Coverage:

- speed math (MB/s, Mbit/s) and averages,
- warmup excluded from statistics,
- exactly `n` samples collected,
- non-2xx response raises,
- `Content-Length` mismatch produces a warning,
- retry succeeds after transient failures and raises when exhausted,
- CLI argument parsing and output rendering.

## Tooling

- `pytest` for tests, `ruff` for linting/formatting.
- GitHub Actions CI runs `ruff check` and `pytest` on Python 3.11 and 3.12.
- Packaging via `pyproject.toml` with a console script
  `internet-speed = internet_speed.cli:main`.
