from __future__ import annotations

from .measurement import (
    MeasurementError,
    aggregate,
    download_once,
    measure_speed,
)
from .models import RequestSample, SpeedResult

__version__ = "1.0.0"

__all__ = [
    "MeasurementError",
    "RequestSample",
    "SpeedResult",
    "aggregate",
    "download_once",
    "measure_speed",
]
