from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from backend.core.config import Config
from backend.core.exceptions import StorageError
from backend.infrastructure.storage.base import StorageAdapter


class S3StorageAdapter(StorageAdapter):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str,
        auto_create_bucket: bool = True,
    ):
        if not bucket:
            raise StorageError(message="S3 bucket is not configured", code="storage_error", status_code=500)

        self.bucket = bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key or None,
            aws_secret_access_key=secret_key or None,
            region_name=region or None,
        )
        if auto_create_bucket:
            self._ensure_bucket()

    @classmethod
    def from_config(cls) -> "S3StorageAdapter":
        return cls(
            endpoint=Config.S3_ENDPOINT,
            access_key=Config.S3_ACCESS_KEY,
            secret_key=Config.S3_SECRET_KEY,
            bucket=Config.S3_BUCKET,
            region=Config.S3_REGION,
            auto_create_bucket=Config.S3_AUTO_CREATE_BUCKET,
        )

    def save(self, object_key: str, content: bytes) -> None:
        try:
            self.client.put_object(Bucket=self.bucket, Key=object_key, Body=content)
        except Exception as exc:
            raise StorageError(
                message="Failed to save document to S3",
                code="storage_error",
                details={"bucket": self.bucket, "object_key": object_key},
            ) from exc

    def read(self, object_key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            body = response["Body"].read()
            if not isinstance(body, bytes):
                body = bytes(body)
            return body
        except Exception as exc:
            raise StorageError(
                message="Failed to read document from S3",
                code="storage_error",
                details={"bucket": self.bucket, "object_key": object_key},
            ) from exc

    def delete(self, object_key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
        except Exception as exc:
            raise StorageError(
                message="Failed to delete document from S3",
                code="storage_error",
                details={"bucket": self.bucket, "object_key": object_key},
            ) from exc

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return
        except ClientError:
            pass
        except Exception as exc:
            raise StorageError(
                message="Failed to access S3 bucket",
                code="storage_error",
                details={"bucket": self.bucket},
            ) from exc

        try:
            self.client.create_bucket(Bucket=self.bucket)
        except Exception as exc:
            raise StorageError(
                message="Failed to create S3 bucket",
                code="storage_error",
                details={"bucket": self.bucket},
            ) from exc
