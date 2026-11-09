"""Abstract interface for document file storage."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional


class FileStorageInterface(ABC):
    """Abstract interface for storing and retrieving uploaded document files."""

    @abstractmethod
    def save_file(self, file_bytes: bytes, filename: str, document_id: str) -> Path:
        """Save file bytes and return the resolved local or staged storage path."""
        pass

    @abstractmethod
    def get_file_bytes(self, document_id: str, object_key: Optional[str] = None) -> bytes:
        """Retrieve raw file bytes from storage."""
        pass

    @abstractmethod
    def get_file_path(self, document_id: str) -> Optional[Path]:
        """Return the local filesystem path for the document if it exists."""
        pass

    @abstractmethod
    def file_exists(self, document_id: str) -> bool:
        """Check if the document file exists in storage."""
        pass

    @abstractmethod
    def delete_file(self, document_id: str) -> bool:
        """Delete the document file from storage."""
        pass

    @abstractmethod
    def get_storage_provider(self) -> str:
        """Return the active storage provider identifier ('local' or 'supabase')."""
        pass

    @abstractmethod
    def get_object_key(self, document_id: str, filename: Optional[str] = None) -> str:
        """Return the unique storage object key for this document."""
        pass

    @abstractmethod
    def check_health(self) -> Dict[str, Any]:
        """Verify storage backend connectivity and health status."""
        pass

