"""Storage infrastructure package exports."""

from typing import Optional
from app.config import get_settings
from app.infrastructure.storage.base import FileStorageInterface
from app.infrastructure.storage.local import LocalFileStorage
from app.infrastructure.storage.supabase_storage import SupabaseStorage

_storage_instance: Optional[FileStorageInterface] = None


def get_file_storage() -> FileStorageInterface:
    """Singleton factory returning the configured FileStorage."""
    global _storage_instance
    if _storage_instance is None:
        settings = get_settings()
        if getattr(settings, "storage_provider", "local").lower() == "supabase" and settings.supabase_url and settings.supabase_key:
            _storage_instance = SupabaseStorage()
        else:
            _storage_instance = LocalFileStorage()
    return _storage_instance


def reset_file_storage() -> None:
    """Reset singleton instance (useful when switching config or in tests)."""
    global _storage_instance
    _storage_instance = None


__all__ = [
    "FileStorageInterface",
    "LocalFileStorage",
    "SupabaseStorage",
    "get_file_storage",
    "reset_file_storage",
]

