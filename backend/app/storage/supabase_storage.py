from __future__ import annotations

from pathlib import Path

import httpx


class SupabaseStorageBackend:
    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        originals_bucket: str,
        exports_bucket: str,
        ocr_raw_bucket: str,
    ) -> None:
        self.base_url = supabase_url.rstrip("/")
        self.service_role_key = service_role_key
        self.originals_bucket = originals_bucket
        self.exports_bucket = exports_bucket
        self.ocr_raw_bucket = ocr_raw_bucket

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    def _bucket_for_key(self, key: str) -> str:
        normalized = key.replace("\\", "/").lstrip("/")
        if "/exports/" in normalized:
            return self.exports_bucket
        if "/ocr-raw/" in normalized or "/ocr_raw/" in normalized:
            return self.ocr_raw_bucket
        return self.originals_bucket

    def _object_url(self, key: str) -> str:
        bucket = self._bucket_for_key(key)
        object_key = key.replace("\\", "/").lstrip("/")
        return f"{self.base_url}/storage/v1/object/{bucket}/{object_key}"

    def save_bytes(self, key: str, content: bytes) -> str:
        headers = {**self._headers, "x-upsert": "true", "Content-Type": "application/octet-stream"}
        response = httpx.post(self._object_url(key), headers=headers, content=content, timeout=30)
        response.raise_for_status()
        return key

    def read_bytes(self, key: str) -> bytes:
        response = httpx.get(self._object_url(key), headers=self._headers, timeout=30)
        response.raise_for_status()
        return response.content

    def local_path(self, key: str) -> Path:
        raise FileNotFoundError(f"Supabase object does not have a local path: {key}")

    def delete(self, key: str) -> None:
        bucket = self._bucket_for_key(key)
        object_key = key.replace("\\", "/").lstrip("/")
        url = f"{self.base_url}/storage/v1/object/{bucket}"
        response = httpx.request(
            "DELETE",
            url,
            headers={**self._headers, "Content-Type": "application/json"},
            json={"prefixes": [object_key]},
            timeout=30,
        )
        response.raise_for_status()
