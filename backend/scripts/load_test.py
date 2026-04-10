"""
Locust WebSocket load test.

Run: locust -f scripts/load_test.py --host ws://localhost:8000
"""

import math
import struct
import time
import uuid

import websocket
from locust import User, between, events, task


def make_sine_pcm(duration_ms: int = 3000, sample_rate: int = 16000) -> bytes:
    n = int(sample_rate * duration_ms / 1000)
    samples = [int(32767 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n)]
    return struct.pack(f"<{n}h", *samples)


SAMPLE_AUDIO = make_sine_pcm()
CHUNK_BYTES = 3200  # 100ms at 16 kHz, 16-bit
API_TOKEN = "dev-token"


class VoiceUser(User):
    wait_time = between(1, 3)

    def on_start(self) -> None:
        self.session_id = str(uuid.uuid4())
        url = f"{self.host}/ws/{self.session_id}?token={API_TOKEN}"
        self.ws = websocket.create_connection(url, timeout=10)
        # Read session_ready control message
        self.ws.recv()

    def on_stop(self) -> None:
        self.ws.close()

    @task
    def stream_utterance(self) -> None:
        start = time.time()
        # Stream 3 seconds of audio in 100ms chunks
        for i in range(0, len(SAMPLE_AUDIO), CHUNK_BYTES):
            chunk = SAMPLE_AUDIO[i : i + CHUNK_BYTES]
            self.ws.send_binary(chunk)
            time.sleep(0.1)

        # Wait for at least one audio response frame (max 10s)
        self.ws.settimeout(10)
        try:
            frame = self.ws.recv()
            latency_ms = (time.time() - start) * 1000
            events.request.fire(
                request_type="WS",
                name="voice_turn",
                response_time=latency_ms,
                response_length=len(frame) if frame else 0,
            )
        except Exception as exc:
            events.request.fire(
                request_type="WS",
                name="voice_turn",
                response_time=(time.time() - start) * 1000,
                response_length=0,
                exception=exc,
            )
