from pathlib import Path


class LocalStorageBackend:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        clean_key = key.replace("\\", "/").lstrip("/")
        path = (self.root / clean_key).resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("storage key escapes storage root")
        return path

    def save_bytes(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    def read_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def local_path(self, key: str) -> Path:
        return self._path(key)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def create_signed_url(self, key: str, expires_in: int = 3600) -> str | None:
        """Local storage does not support signed URLs."""
        return None

