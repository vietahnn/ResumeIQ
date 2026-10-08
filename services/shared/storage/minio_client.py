import io
from typing import Optional
from minio import Minio
from minio.error import S3Error
from services.shared.config import settings


class MinioStorageService:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.default_bucket = settings.MINIO_BUCKET
        self._bucket_verified = False

    def ensure_bucket_exists(self, bucket_name: str) -> None:
        if self._bucket_verified:
            return
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
            self._bucket_verified = True
        except Exception as err:
            pass

    # Uploads in-memory binary data to the target object storage bucket
    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket_name: Optional[str] = None
    ) -> str:
        target_bucket = bucket_name or self.default_bucket
        stream = io.BytesIO(data)
        self.client.put_object(
            bucket_name=target_bucket,
            object_name=object_name,
            data=stream,
            length=len(data),
            content_type=content_type
        )
        return object_name

    def download_bytes(self, object_name: str, bucket_name: Optional[str] = None) -> bytes:
        target_bucket = bucket_name or self.default_bucket
        response = self.client.get_object(target_bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


minio_storage = MinioStorageService()
