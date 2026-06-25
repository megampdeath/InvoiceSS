from app.core.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.supabase_storage import SupabaseStorageBackend


def get_storage_backend() -> StorageBackend:
    settings = get_settings()
    if settings.STORAGE_BACKEND.lower() == "supabase":
        service_role_key = settings.SUPABASE_SERVICE_ROLE_KEY
        if not settings.SUPABASE_URL or not service_role_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase storage.")
        return SupabaseStorageBackend(
            settings.SUPABASE_URL,
            service_role_key,
            settings.SUPABASE_STORAGE_ORIGINALS_BUCKET,
            settings.SUPABASE_STORAGE_EXPORTS_BUCKET,
            settings.SUPABASE_STORAGE_OCR_RAW_BUCKET,
        )
    return LocalStorageBackend(settings.local_storage_path)
