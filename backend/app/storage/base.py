from pathlib import Path
from typing import Protocol


class StorageBackend(Protocol):
    def save_bytes(self, key: str, content: bytes) -> str:
        ...

    def read_bytes(self, key: str) -> bytes:
        ...

    def local_path(self, key: str) -> Path:
        ...

    def delete(self, key: str) -> None:
        ...

    def create_signed_url(self, key: str, expires_in: int = 3600) -> str | None:
        """Return a time-limited download URL, or None if not supported."""
        ...

