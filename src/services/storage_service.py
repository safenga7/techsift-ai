"""
TechSift AI - Storage Service.
Manages secure local file operations, path traversal prevention, and atomic storage.
"""

import hashlib
from pathlib import Path
import re
import uuid
from src.core.config import settings
from src.core.exceptions import StorageError


class StorageService:
    """Manages secure local filesystem persistence for uploaded documents."""

    def __init__(self, base_dir: Path = settings.DOCUMENTS_DIR):
        self.base_dir = base_dir.resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize user-provided filename:
        - Strips path components (directory traversal prevention).
        - Replaces unsafe characters.
        - Preserves extension.
        """
        # Strip directory parts
        clean_name = Path(filename).name
        # Keep alphanumeric, dots, dashes, underscores
        clean_name = re.sub(r"[^\w\.\-]", "_", clean_name)
        # Prevent hidden files
        clean_name = clean_name.lstrip(".")
        return clean_name or "document"

    def generate_storage_filename(self, original_filename: str) -> str:
        """Generate collision-free storage filename combining UUID and safe extension."""
        ext = Path(original_filename).suffix.lower()
        unique_id = str(uuid.uuid4())
        return f"{unique_id}{ext}"

    def compute_sha256(self, content: bytes) -> str:
        """Compute SHA-256 digest for file content."""
        return hashlib.sha256(content).hexdigest()

    def get_absolute_path(self, storage_filename: str) -> Path:
        """
        Resolves the absolute path and enforces directory sandboxing
        to strictly prevent path traversal attacks.
        """
        target = (self.base_dir / storage_filename).resolve()
        if not target.is_relative_to(self.base_dir):
            raise StorageError("Path traversal attempt detected.")
        return target

    async def save_file(self, content: bytes, storage_filename: str) -> Path:
        """Write file bytes to sandboxed storage location."""
        try:
            target_path = self.get_absolute_path(storage_filename)
            # Write bytes synchronously or via threadpool
            target_path.write_bytes(content)
            return target_path
        except Exception as exc:
            raise StorageError(f"Failed to persist file to storage: {str(exc)}") from exc

    def delete_file(self, storage_filename: str) -> bool:
        """Remove file from storage if it exists. Returns True if deleted."""
        try:
            target_path = self.get_absolute_path(storage_filename)
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
                return True
            return False
        except Exception as exc:
            raise StorageError(f"Failed to delete file from storage: {str(exc)}") from exc

    def read_file(self, storage_filename: str) -> bytes:
        """Read file content from storage."""
        try:
            target_path = self.get_absolute_path(storage_filename)
            if not target_path.exists():
                raise StorageError("Target storage file does not exist.")
            return target_path.read_bytes()
        except Exception as exc:
            raise StorageError(f"Failed to read file from storage: {str(exc)}") from exc


storage_service = StorageService()
