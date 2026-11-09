"""Supabase private bucket storage implementation with local staging cache."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import get_settings
from app.infrastructure.storage.base import FileStorageInterface

logger = logging.getLogger(__name__)


class SupabaseStorage(FileStorageInterface):
    """Production Supabase Storage implementation for private buckets."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        cache_dir: Optional[str] = None,
    ):
        settings = get_settings()
        self.supabase_url = (supabase_url or settings.supabase_url or "").rstrip("/")
        self.supabase_key = supabase_key or settings.supabase_key or ""
        self.bucket_name = bucket_name or settings.supabase_storage_bucket or "financial-documents"
        self.cache_dir = Path(cache_dir or settings.upload_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        if not self.supabase_url or not self.supabase_key:
            logger.warning(
                "SupabaseStorage initialized without complete credentials. "
                "Ensure SUPABASE_URL and SUPABASE_KEY are configured in .env."
            )

        # Attempt to initialize official Supabase Python SDK client if installed
        self._sdk_client = None
        try:
            from supabase import create_client
            if self.supabase_url and self.supabase_key:
                self._sdk_client = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase Python SDK client initialized successfully.")
        except ImportError:
            logger.info("supabase-py SDK not installed; utilizing high-performance native HTTP REST client.")
        except Exception as e:
            logger.warning("Supabase SDK initialization returned warning: %s; falling back to REST client.", e)

    def _get_headers(self, content_type: Optional[str] = None) -> Dict[str, str]:
        """Construct secure authorization headers for Supabase Storage API."""
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    def get_storage_provider(self) -> str:
        return "supabase"

    def get_object_key(self, document_id: str, filename: Optional[str] = None) -> str:
        """Deterministic object key within the private bucket."""
        return f"{document_id}.pdf"

    def save_file(self, file_bytes: bytes, filename: str, document_id: str) -> Path:
        """Upload raw PDF bytes to private Supabase bucket and stage in local cache.

        Raises:
            RuntimeError: If upload to Supabase Storage fails.
        """
        if not file_bytes:
            raise ValueError("Uploaded file bytes cannot be empty.")

        if not self.supabase_url or not self.supabase_key:
            raise RuntimeError(
                "Cannot upload to Supabase Storage: SUPABASE_URL or SUPABASE_KEY is missing."
            )

        object_key = self.get_object_key(document_id, filename)
        logger.info(
            "Uploading %d bytes to Supabase Storage bucket '%s' with object key '%s'...",
            len(file_bytes),
            self.bucket_name,
            object_key,
        )

        uploaded = False
        last_error = None

        # 1. Try via official Supabase SDK if available
        if self._sdk_client:
            try:
                self._sdk_client.storage.from_(self.bucket_name).upload(
                    path=object_key,
                    file=file_bytes,
                    file_options={"content-type": "application/pdf", "upsert": "true"},
                )
                uploaded = True
                logger.info("Uploaded object '%s' to bucket '%s' via Supabase SDK.", object_key, self.bucket_name)
            except Exception as e:
                logger.warning("Supabase SDK upload failed (%s); trying REST API fallback.", e)
                last_error = e

        # 2. Fallback / direct REST API client
        if not uploaded:
            import httpx
            url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{object_key}"
            headers = self._get_headers(content_type="application/pdf")
            headers["x-upsert"] = "true"

            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, headers=headers, content=file_bytes)
                    if resp.status_code in (200, 201):
                        uploaded = True
                        logger.info("Uploaded object '%s' to bucket '%s' via Supabase REST API.", object_key, self.bucket_name)
                    else:
                        err_msg = f"Supabase Storage HTTP {resp.status_code}: {resp.text}"
                        logger.error("Upload failed: %s", err_msg)
                        raise RuntimeError(f"Failed to upload document to Supabase Storage: {err_msg}")
            except httpx.RequestError as exc:
                raise RuntimeError(f"Network error uploading to Supabase Storage: {exc}") from exc

        if not uploaded:
            raise RuntimeError(f"Failed to upload document to Supabase Storage: {last_error}")

        # Stage in local cache for immediate downstream processing
        cache_path = self.cache_dir / object_key
        cache_path.write_bytes(file_bytes)
        return cache_path

    def get_file_bytes(self, document_id: str, object_key: Optional[str] = None) -> bytes:
        """Retrieve raw PDF bytes directly from Supabase Storage."""
        key = object_key or self.get_object_key(document_id)
        if not self.supabase_url or not self.supabase_key:
            cache_path = self.cache_dir / key
            if cache_path.is_file():
                return cache_path.read_bytes()
            raise RuntimeError("Supabase Storage credentials not configured and file not in cache.")

        # 1. Try via Supabase SDK
        if self._sdk_client:
            try:
                data = self._sdk_client.storage.from_(self.bucket_name).download(key)
                if data:
                    (self.cache_dir / key).write_bytes(data)
                    return data
            except Exception as e:
                logger.debug("SDK download failed for %s (%s); trying REST endpoint...", key, e)

        # 2. Try via REST API
        import httpx
        headers = self._get_headers()
        urls_to_try = [
            f"{self.supabase_url}/storage/v1/object/authenticated/{self.bucket_name}/{key}",
            f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{key}",
        ]

        last_status = 404
        last_body = ""
        for url in urls_to_try:
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        content = resp.content
                        (self.cache_dir / key).write_bytes(content)
                        return content
                    last_status = resp.status_code
                    last_body = resp.text
            except Exception as e:
                logger.debug("REST download attempt failed for %s: %s", url, e)

        # Fallback to local staging cache if network fails
        cache_path = self.cache_dir / key
        if cache_path.is_file():
            logger.info("Serving document %s from local staging cache.", document_id)
            return cache_path.read_bytes()

        if last_status == 404:
            raise FileNotFoundError(
                f"Document object '{key}' not found in Supabase bucket '{self.bucket_name}'."
            )
        raise RuntimeError(
            f"Failed to retrieve document '{key}' from Supabase Storage (HTTP {last_status}): {last_body}"
        )

    def get_file_path(self, document_id: str) -> Optional[Path]:
        """Return local cached filesystem path for document, fetching from Supabase if needed."""
        key = self.get_object_key(document_id)
        cache_path = self.cache_dir / key
        if cache_path.is_file():
            return cache_path

        try:
            self.get_file_bytes(document_id, object_key=key)
            if cache_path.is_file():
                return cache_path
        except Exception as e:
            logger.debug("Could not resolve file path from Supabase for %s: %s", document_id, e)

        return None

    def file_exists(self, document_id: str) -> bool:
        """Check if document object exists in Supabase Storage or local cache."""
        key = self.get_object_key(document_id)
        if (self.cache_dir / key).is_file():
            return True

        if not self.supabase_url or not self.supabase_key:
            return False

        if self._sdk_client:
            try:
                res = self._sdk_client.storage.from_(self.bucket_name).list(
                    path="",
                    options={"search": key, "limit": 1},
                )
                if any(item.get("name") == key for item in res):
                    return True
            except Exception:
                pass

        import httpx
        url = f"{self.supabase_url}/storage/v1/object/list/{self.bucket_name}"
        headers = self._get_headers(content_type="application/json")
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(url, headers=headers, json={"prefix": key, "limit": 1})
                if resp.status_code == 200:
                    data = resp.json()
                    return any(item.get("name") == key for item in data)
        except Exception:
            pass

        return False

    def delete_file(self, document_id: str) -> bool:
        """Delete object from Supabase bucket and local cache."""
        key = self.get_object_key(document_id)
        cache_path = self.cache_dir / key
        if cache_path.is_file():
            try:
                cache_path.unlink()
            except Exception:
                pass

        if not self.supabase_url or not self.supabase_key:
            return True

        if self._sdk_client:
            try:
                self._sdk_client.storage.from_(self.bucket_name).remove([key])
                return True
            except Exception as e:
                logger.warning("Supabase SDK remove failed: %s", e)

        import httpx
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}"
        headers = self._get_headers(content_type="application/json")
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.request("DELETE", url, headers=headers, json={"prefixes": [key]})
                return resp.status_code in (200, 204)
        except Exception as e:
            logger.warning("Failed to delete object '%s' from Supabase: %s", key, e)
            return False

    def check_health(self) -> Dict[str, Any]:
        """Verify Supabase Storage connection and private bucket accessibility."""
        if not self.supabase_url or not self.supabase_key:
            return {
                "healthy": False,
                "provider": "supabase",
                "bucket": self.bucket_name,
                "error": "SUPABASE_URL or SUPABASE_KEY not configured",
            }

        # 1. Try via SDK
        if self._sdk_client:
            try:
                b = self._sdk_client.storage.get_bucket(self.bucket_name)
                return {
                    "healthy": True,
                    "provider": "supabase",
                    "bucket": self.bucket_name,
                    "public": getattr(b, "public", False) if hasattr(b, "public") else False,
                    "status": "connected_to_private_bucket",
                    "client": "supabase-py-sdk",
                }
            except Exception as e:
                logger.debug("SDK health probe returned: %s; trying REST probe...", e)

        # 2. Try via REST
        import httpx
        url = f"{self.supabase_url}/storage/v1/bucket/{self.bucket_name}"
        headers = self._get_headers()
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    info = resp.json()
                    return {
                        "healthy": True,
                        "provider": "supabase",
                        "bucket": self.bucket_name,
                        "public": info.get("public", False),
                        "file_size_limit": info.get("file_size_limit"),
                        "status": "connected_to_private_bucket",
                        "client": "native-rest",
                    }
                elif resp.status_code == 404:
                    return {
                        "healthy": False,
                        "provider": "supabase",
                        "bucket": self.bucket_name,
                        "error": f"Bucket '{self.bucket_name}' not found. Please create the private bucket in the Supabase Dashboard under Storage.",
                    }
                elif resp.status_code in (401, 403):
                    return {
                        "healthy": False,
                        "provider": "supabase",
                        "bucket": self.bucket_name,
                        "error": "Authentication error: SUPABASE_KEY is invalid or lacks storage permissions.",
                    }
                else:
                    return {
                        "healthy": False,
                        "provider": "supabase",
                        "bucket": self.bucket_name,
                        "error": f"Supabase Storage returned HTTP {resp.status_code}: {resp.text}",
                    }
        except httpx.RequestError as exc:
            return {
                "healthy": False,
                "provider": "supabase",
                "bucket": self.bucket_name,
                "error": f"Connection error reaching Supabase Storage: {exc}",
            }
