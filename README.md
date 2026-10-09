# internet-speed

A small console utility that measures download throughput against a URL. It
performs a fixed number of sequential HTTP requests, waits for each response,
and reports the average request time, the total downloaded volume, and the
resulting speed in MB/s (and Mbit/s).

## Features

- sequential HTTP requests (10 by default), timed and summed per request;
- a warmup request that establishes the connection and is excluded from stats;
- per-request and aggregate reporting: bytes, time, MB/s;
- retries with backoff on transient network failures;
- no state, no config files — one URL in, a report out.

## Requirements

- Python 3.11+
- [`requests`](https://requests.readthedocs.io/) (installed automatically)

## Installation

With [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

With pip:

```bash
python -m pip install -e .
```

## Usage

```bash
# install a console script
internet-speed <URL>

# or run the module directly
python -m internet_speed <URL>
```

`URL` is any address that serves a reasonably large payload — a big image, a
video segment, or a download endpoint. For example:

```bash
internet-speed "https://speed.cloudflare.com/__down?bytes=10000000"
python -m internet_speed "https://picsum.photos/4000/4000" -n 5
```

### Options

| Option           | Default | Description                              |
| ---------------- | ------- | ---------------------------------------- |
| `-n`, `--requests` | `10`    | number of measured requests               |
| `--chunk-size`   | `65536` | streaming chunk size in bytes             |
| `--timeout`      | `30`    | per-request timeout in seconds            |
| `--no-warmup`    | off     | skip the warmup request                   |
| `--retries`      | `2`     | retries per failed request (with backoff) |

### Example output

```
Target: https://speed.cloudflare.com/__down?bytes=3000000
Requests: 3 (warmup: yes, chunk: 65.536 KB)

  #  status         bytes   time (s)       MB/s
  1     200      3.000 MB      0.109     27.516
  2     200      3.000 MB      0.191     15.695
  3     200      3.000 MB      0.097     30.911
------------------------------------------------
Total:            9.000 MB in 0.40 s
Average request:  3.000 MB in 0.13 s
Download speed:   22.66 MB/s  (181.25 Mbit/s)
```

Exit codes: `0` on success, `2` for invalid arguments, `1` for a failed
measurement.

## How the measurement works

The methodology follows the hygiene used by common speedtest tools:

1. A **warmup** request resolves DNS and opens the TCP/TLS connection, which is
   then reused through a single keep-alive session. The warmup is not counted.
2. Each measured request streams the response body and times the full
   request/response cycle with a monotonic clock.
3. Only bytes actually transferred are counted: the client sends
   `Accept-Encoding: identity` so the response is not decompressed before
   counting.
4. Speed is a time-weighted throughput: `total_bytes / total_seconds`.
5. `Content-Length`, when present, is compared against the received byte count
   and a mismatch is reported as a warning.

### Units

Units are decimal, matching network speed conventions:

- `MB/s = bytes_per_second / 1_000_000`
- `Mbit/s = bytes_per_second * 8 / 1_000_000`

## Limitations

- The result is limited by the remote server, the network path, and the
  request timeout — it is not a controlled throughput benchmark.
- Requests are sequential by design, so a single connection may not saturate a
  very high-bandwidth link.
- No upload, latency, or jitter measurement.

## Development

```bash
uv sync
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pytest            # tests (no network access required)
```
