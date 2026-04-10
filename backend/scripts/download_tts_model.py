"""Pre-download Coqui TTS model into the Docker image layer."""
import os
from TTS.api import TTS

model_name = os.getenv("TTS_MODEL_NAME", "tts_models/en/ljspeech/fast_pitch")
model_dir = os.getenv("TTS_MODEL_DIR", "/app/models/tts")

os.makedirs(model_dir, exist_ok=True)
print(f"Downloading TTS model: {model_name} -> {model_dir}")
TTS(model_name=model_name, progress_bar=False)
print("TTS model downloaded.")
