"""Domain exception hierarchy."""


class VoiceAIError(Exception):
    """Base exception for all domain errors."""

    def __init__(self, message: str, retriable: bool = False) -> None:
        super().__init__(message)
        self.retriable = retriable


class ASRError(VoiceAIError):
    """Raised when Whisper transcription fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retriable=True)


class LLMError(VoiceAIError):
    """Raised when the LLM API call fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retriable=True)


class TTSError(VoiceAIError):
    """Raised when TTS synthesis fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retriable=True)


class SessionNotFoundError(VoiceAIError):
    """Raised when a session_id does not exist in Redis."""

    def __init__(self, session_id: str) -> None:
        super().__init__(f"Session not found: {session_id}", retriable=False)
        self.session_id = session_id


class AudioFormatError(VoiceAIError):
    """Raised when incoming audio bytes are malformed."""

    def __init__(self, message: str) -> None:
        super().__init__(message, retriable=False)


class AuthenticationError(VoiceAIError):
    """Raised when the WebSocket auth token is invalid."""

    def __init__(self) -> None:
        super().__init__("Invalid or missing authentication token", retriable=False)
