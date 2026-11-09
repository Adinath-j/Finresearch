"""Local filesystem storage implementation."""

from pathlib import Path
from typing import Any, Dict, Optional

from app.config import get_settings
from app.infrastructure.storage.base import FileStorageInterface


class LocalFileStorage(FileStorageInterface):
    """Stores uploaded document files on the local filesystem."""

    def __init__(self, upload_dir: Optional[str] = None):
        self.upload_dir = Path(upload_dir or get_settings().upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_bytes: bytes, filename: str, document_id: str) -> Path:
        target_path = self.upload_dir / f"{document_id}.pdf"
        target_path.write_bytes(file_bytes)
        return target_path

    def get_file_bytes(self, document_id: str, object_key: Optional[str] = None) -> bytes:
        target_path = self.get_file_path(document_id)
        if target_path and target_path.is_file():
            return target_path.read_bytes()
        raise FileNotFoundError(f"File for document {document_id} not found in local storage.")

    def get_file_path(self, document_id: str) -> Optional[Path]:
        target_path = self.upload_dir / f"{document_id}.pdf"
        if target_path.is_file():
            return target_path
        return None

    def file_exists(self, document_id: str) -> bool:
        return self.get_file_path(document_id) is not None

    def delete_file(self, document_id: str) -> bool:
        target_path = self.get_file_path(document_id)
        if target_path and target_path.is_file():
            target_path.unlink()
            return True
        return False

    def get_storage_provider(self) -> str:
        return "local"

    def get_object_key(self, document_id: str, filename: Optional[str] = None) -> str:
        return f"{document_id}.pdf"

    def check_health(self) -> Dict[str, Any]:
        exists = self.upload_dir.exists()
        writable = False
        if exists:
            try:
                test_file = self.upload_dir / ".health_check.tmp"
                test_file.write_text("ok")
                test_file.unlink()
                writable = True
            except Exception:
                writable = False
        return {
            "healthy": exists and writable,
            "provider": "local",
            "upload_dir": str(self.upload_dir),
            "writable": writable,
        }

