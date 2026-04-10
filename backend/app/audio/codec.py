"""Opus encode/decode wrappers around opuslib."""

from __future__ import annotations

import opuslib

from app.config import get_settings


def _make_encoder(sample_rate: int, channels: int, bitrate: int) -> opuslib.Encoder:
    enc = opuslib.Encoder(sample_rate, channels, opuslib.APPLICATION_VOIP)
    enc.bitrate = bitrate
    return enc


def _make_decoder(sample_rate: int, channels: int) -> opuslib.Decoder:
    return opuslib.Decoder(sample_rate, channels)


def encode_pcm_to_opus(pcm_bytes: bytes, sample_rate: int | None = None, channels: int = 1) -> bytes:
    """Encode raw PCM int16 LE bytes to Opus."""
    settings = get_settings()
    sr = sample_rate or settings.tts_output_sample_rate
    bitrate = settings.opus_bitrate
    # Frame size: 20ms at the given sample rate
    frame_size = sr // 50
    encoder = _make_encoder(sr, channels, bitrate)
    # Opus requires exactly frame_size samples per call; pad if needed
    samples_needed = frame_size * channels * 2  # 2 bytes per int16 sample
    if len(pcm_bytes) < samples_needed:
        pcm_bytes = pcm_bytes + b"\x00" * (samples_needed - len(pcm_bytes))
    return encoder.encode(pcm_bytes[:samples_needed], frame_size)


def decode_opus_to_pcm(opus_bytes: bytes, sample_rate: int | None = None, channels: int = 1) -> bytes:
    """Decode Opus bytes to raw PCM int16 LE bytes."""
    settings = get_settings()
    sr = sample_rate or settings.tts_output_sample_rate
    frame_size = sr // 50  # 20ms
    decoder = _make_decoder(sr, channels)
    return decoder.decode(opus_bytes, frame_size)
