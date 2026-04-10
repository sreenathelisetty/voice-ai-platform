"""Pre-download Whisper model into the Docker image layer."""
import os
import whisper

model_size = os.getenv("WHISPER_MODEL_SIZE", "small.en")
model_dir = os.getenv("WHISPER_MODEL_DIR", "/app/models/whisper")

print(f"Downloading Whisper model: {model_size} -> {model_dir}")
whisper.load_model(model_size, download_root=model_dir)
print("Whisper model downloaded.")
