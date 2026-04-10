"""
AWS CloudWatch Embedded Metrics Format (EMF) emitter.
Writes structured JSON to stdout — CW Logs Agent picks it up automatically.
No boto3 dependency required.
"""

from __future__ import annotations

import json
import time

from app.config import get_settings


def put_metric(
    name: str,
    value: float,
    unit: str = "Milliseconds",
    dimensions: dict[str, str] | None = None,
) -> None:
    """Emit a single metric in EMF format."""
    settings = get_settings()
    dims = dimensions or {}
    dim_keys = list(dims.keys())

    emf = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": "VoiceAI",
                    "Dimensions": [dim_keys] if dim_keys else [[]],
                    "Metrics": [{"Name": name, "Unit": unit}],
                }
            ],
        },
        name: value,
        "LogGroup": settings.aws_cloudwatch_log_group,
        **dims,
    }
    print(json.dumps(emf), flush=True)
