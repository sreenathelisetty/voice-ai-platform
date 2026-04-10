"""Sample rate conversion utilities."""

import numpy as np


def resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """
    Resample audio from orig_sr to target_sr.
    Accepts float32 arrays normalised to [-1, 1].
    """
    if orig_sr == target_sr:
        return audio
    import librosa  # lazy import — heavy dependency
    return librosa.resample(audio, orig_sr=orig_sr, target_sr=target_sr, res_type="kaiser_best")


def pcm_bytes_to_float32(pcm: bytes, sample_width: int = 2) -> np.ndarray:
    """Convert raw PCM bytes (int16 LE) to float32 [-1, 1]."""
    dtype = np.int16 if sample_width == 2 else np.int8
    audio = np.frombuffer(pcm, dtype=dtype).astype(np.float32)
    audio /= float(np.iinfo(dtype).max)
    return audio


def float32_to_pcm_bytes(audio: np.ndarray) -> bytes:
    """Convert float32 [-1, 1] back to int16 PCM bytes."""
    clipped = np.clip(audio, -1.0, 1.0)
    return (clipped * 32767).astype(np.int16).tobytes()
