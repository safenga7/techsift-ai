"""
TechSift AI - Custom Application Exceptions & Error Hierarchy.
"""

from typing import Any, Optional


class AppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' was not found.",
            code="RESOURCE_NOT_FOUND",
            status_code=404,
        )


class FileValidationError(AppException):
    """Raised when file upload fails type, signature, or extension validation."""

    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(
            message=message,
            code="INVALID_FILE_FORMAT",
            status_code=400,
            details=details,
        )


class FileTooLargeError(AppException):
    """Raised when an uploaded file exceeds the configured size limit."""

    def __init__(self, file_size: int, max_size: int):
        super().__init__(
            message=(
                f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum "
                f"allowed limit ({max_size / (1024 * 1024):.2f} MB)."
            ),
            code="FILE_TOO_LARGE",
            status_code=413,
            details={"file_size": file_size, "max_size": max_size},
        )


class UnsupportedDocumentError(AppException):
    """Raised when document content is unreadable (e.g. scanned image-only PDF)."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="UNSUPPORTED_DOCUMENT_CONTENT",
            status_code=422,
        )


class StorageError(AppException):
    """Raised when local file I/O operations fail."""

    def __init__(self, message: str):
        super().__init__(
            message=message,
            code="STORAGE_ERROR",
            status_code=500,
        )


class AIProviderException(AppException):
    """Base exception for AI provider operations."""

    def __init__(
        self,
        message: str = "AI service encountered an error.",
        code: str = "AI_SERVICE_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class RateLimitExceededError(AIProviderException):
    """Raised when free-tier rate limit (RPM/RPD) is exhausted."""

    def __init__(
        self,
        message: str = "Google Gemini free-tier rate limit reached. Please wait a moment before retrying.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details=details,
        )


class AIAuthenticationError(AIProviderException):
    """Raised when API key is missing or invalid."""

    def __init__(
        self,
        message: str = "AI service authentication failed.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="AI_AUTHENTICATION_ERROR",
            status_code=500,
            details=details,
        )


class AITimeoutError(AIProviderException):
    """Raised when a request exceeds the configured timeout threshold."""

    def __init__(
        self,
        message: str = "AI service request timed out.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="AI_REQUEST_TIMEOUT",
            status_code=504,
            details=details,
        )


class AIModelUnavailableError(AIProviderException):
    """Raised when the requested model is sunset or unavailable."""

    def __init__(
        self,
        message: str = "Requested AI model is unavailable or sunset.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="AI_MODEL_UNAVAILABLE",
            status_code=503,
            details=details,
        )


class AudioProviderException(AppException):
    """Base exception for audio synthesis and TTS operations."""

    def __init__(
        self,
        message: str = "Audio synthesis service encountered an error.",
        code: str = "AUDIO_SERVICE_ERROR",
        status_code: int = 500,
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=status_code,
            details=details,
        )


class TTSConnectionError(AudioProviderException):
    """Raised when TTS remote service cannot be reached or handshakes fail."""

    def __init__(
        self,
        message: str = "Text-to-Speech synthesis service is currently unreachable.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="TTS_CONNECTION_ERROR",
            status_code=503,
            details=details,
        )


class TTSVoiceUnavailableError(AudioProviderException):
    """Raised when requested voice identifier is not supported."""

    def __init__(
        self,
        message: str = "The requested speech voice is unavailable.",
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="TTS_VOICE_UNAVAILABLE",
            status_code=400,
            details=details,
        )


class AudioDependencyError(AudioProviderException):
    """Raised when system audio tools (e.g. ffmpeg / ffprobe) are missing from PATH."""

    def __init__(
        self,
        message: str = (
            "ffmpeg is required for audio synthesis and stitching but was not found on the system PATH. "
            "Please install ffmpeg: macOS: 'brew install ffmpeg' | Ubuntu/Linux: 'sudo apt install ffmpeg' | Windows: 'winget install Gyan.FFmpeg'."
        ),
        details: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            code="AUDIO_DEPENDENCY_MISSING",
            status_code=503,
            details=details,
        )


