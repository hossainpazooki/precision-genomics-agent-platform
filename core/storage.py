"""Storage backend abstraction for local filesystem and GCS."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


@runtime_checkable
class StorageBackend(Protocol):
    """Protocol for storage backends."""

    def read_bytes(self, path: str) -> bytes: ...
    def write_bytes(self, path: str, data: bytes) -> None: ...
    def list_files(self, prefix: str) -> list[str]: ...


class LocalStorageBackend:
    """Local filesystem storage backend."""

    def __init__(self, base_dir: str | Path = ".") -> None:
        self.base_dir = Path(base_dir)

    def read_bytes(self, path: str) -> bytes:
        return (self.base_dir / path).read_bytes()

    def write_bytes(self, path: str, data: bytes) -> None:
        full_path = self.base_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)

    def list_files(self, prefix: str) -> list[str]:
        base = self.base_dir / prefix
        if not base.exists():
            return []
        return [str(p.relative_to(self.base_dir)) for p in base.rglob("*") if p.is_file()]


class GCSStorageBackend:
    """Google Cloud Storage backend."""

    def __init__(self, bucket_name: str) -> None:
        from google.cloud.storage import Client

        self.client = Client()
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name

    def read_bytes(self, path: str) -> bytes:
        blob = self.bucket.blob(path)
        return blob.download_as_bytes()

    def write_bytes(self, path: str, data: bytes) -> None:
        blob = self.bucket.blob(path)
        blob.upload_from_string(data)

    def list_files(self, prefix: str) -> list[str]:
        blobs = self.client.list_blobs(self.bucket_name, prefix=prefix)
        return [blob.name for blob in blobs]


def get_storage_backend(bucket_name: str | None = None, base_dir: str | Path = ".") -> StorageBackend:
    """Factory: returns GCS backend when bucket is set, otherwise local."""
    if bucket_name:
        return GCSStorageBackend(bucket_name)
    return LocalStorageBackend(base_dir)
