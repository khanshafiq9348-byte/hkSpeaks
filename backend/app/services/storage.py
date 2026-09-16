import os
import io
import uuid
from typing import Optional
from app.core.config import settings

class StorageService:
    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER
        self.local_dir = os.path.abspath(settings.STORAGE_LOCAL_DIR)
        os.makedirs(self.local_dir, exist_ok=True)

    async def upload_audio(self, key: str, audio_bytes: bytes, content_type: str = "audio/mpeg") -> str:
        """
        Uploads audio to storage (local or S3) and returns the public/accessible URL.
        """
        if self.provider in ["s3", "r2", "minio"]:
            # Production S3 / Cloudflare R2 / MinIO
            import boto3
            session = boto3.session.Session()
            client = session.client(
                "s3",
                endpoint_url=settings.STORAGE_ENDPOINT_URL,
                aws_access_key_id=settings.STORAGE_ACCESS_KEY_ID,
                aws_secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY,
                region_name=settings.STORAGE_REGION
            )
            client.put_object(
                Bucket=settings.STORAGE_BUCKET_NAME,
                Key=key,
                Body=audio_bytes,
                ContentType=content_type
            )
            # Generate signed URL or CDN URL
            return f"{settings.STORAGE_PUBLIC_URL_BASE}/{key}"

        # Local storage provider
        safe_rel_path = key.replace("/", os.sep)
        full_path = os.path.join(self.local_dir, safe_rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, "wb") as f:
            f.write(audio_bytes)

        return f"{settings.STORAGE_PUBLIC_URL_BASE}/{key}"

    def get_local_path(self, key: str) -> Optional[str]:
        safe_rel_path = key.replace("/", os.sep)
        full_path = os.path.join(self.local_dir, safe_rel_path)
        if os.path.exists(full_path):
            return full_path
        return None

    async def delete_audio(self, key: str):
        if self.provider in ["s3", "r2", "minio"]:
            import boto3
            client = boto3.client("s3", endpoint_url=settings.STORAGE_ENDPOINT_URL)
            client.delete_object(Bucket=settings.STORAGE_BUCKET_NAME, Key=key)
            return

        safe_rel_path = key.replace("/", os.sep)
        full_path = os.path.join(self.local_dir, safe_rel_path)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception:
                pass

    def save_file_sync(self, file_bytes: bytes, filename: str, user_id: str, category: str = "general", mime_type: str = "application/octet-stream") -> tuple[str, str]:
        key = f"users/{user_id}/{category}/{filename}"
        safe_rel_path = key.replace("/", os.sep)
        full_path = os.path.join(self.local_dir, safe_rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file_bytes)
        url = f"{settings.STORAGE_PUBLIC_URL_BASE}/{key}"
        return full_path, url

    async def save_file(self, file_bytes: bytes, filename: str, user_id: str, category: str = "general", mime_type: str = "application/octet-stream") -> tuple[str, str]:
        return self.save_file_sync(file_bytes, filename, user_id, category, mime_type)

storage_service = StorageService()
