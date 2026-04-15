import tempfile
import unittest
from io import BytesIO
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError

from backend.core.exceptions import StorageError
from backend.infrastructure.storage.factory import create_storage_adapter
from backend.infrastructure.storage.local import LocalFileStorageAdapter
from backend.infrastructure.storage.s3 import S3StorageAdapter


class LocalFileStorageAdapterTestCase(unittest.TestCase):
    def test_save_and_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            storage.save("a/b/test.txt", b"hello")
            data = storage.read("a/b/test.txt")
            self.assertEqual(data, b"hello")

    def test_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = LocalFileStorageAdapter(temp_dir)
            with self.assertRaises(StorageError):
                storage.save("../outside.txt", b"x")


class S3StorageAdapterTestCase(unittest.TestCase):
    @patch("backend.infrastructure.storage.s3.boto3.client")
    def test_save_and_read_roundtrip(self, boto_client_mock):
        client = Mock()
        client.get_object.return_value = {"Body": BytesIO(b"hello-s3")}
        boto_client_mock.return_value = client

        storage = S3StorageAdapter(
            endpoint="http://localhost:9000",
            access_key="minio",
            secret_key="secret",
            bucket="rag-documents",
            region="us-east-1",
            auto_create_bucket=False,
        )
        storage.save("docs/test.txt", b"hello-s3")
        content = storage.read("docs/test.txt")

        client.put_object.assert_called_once()
        client.get_object.assert_called_once_with(Bucket="rag-documents", Key="docs/test.txt")
        self.assertEqual(content, b"hello-s3")

    @patch("backend.infrastructure.storage.s3.boto3.client")
    def test_auto_create_bucket_if_head_fails(self, boto_client_mock):
        client = Mock()
        client.head_bucket.side_effect = ClientError(
            error_response={"Error": {"Code": "404", "Message": "Not found"}},
            operation_name="HeadBucket",
        )
        boto_client_mock.return_value = client

        _ = S3StorageAdapter(
            endpoint="http://localhost:9000",
            access_key="minio",
            secret_key="secret",
            bucket="rag-documents",
            region="us-east-1",
            auto_create_bucket=True,
        )
        client.create_bucket.assert_called_once_with(Bucket="rag-documents")

    @patch("backend.infrastructure.storage.s3.boto3.client")
    def test_raises_storage_error_on_save_failure(self, boto_client_mock):
        client = Mock()
        client.put_object.side_effect = Exception("boom")
        boto_client_mock.return_value = client

        storage = S3StorageAdapter(
            endpoint="http://localhost:9000",
            access_key="minio",
            secret_key="secret",
            bucket="rag-documents",
            region="us-east-1",
            auto_create_bucket=False,
        )
        with self.assertRaises(StorageError):
            storage.save("k", b"v")


class StorageFactoryTestCase(unittest.TestCase):
    @patch("backend.infrastructure.storage.factory.Config.STORAGE_BACKEND", "local")
    @patch("backend.infrastructure.storage.factory.Config.DOCUMENTS_STORAGE_PATH", "/tmp/factory-test")
    def test_factory_returns_local_adapter(self):
        adapter = create_storage_adapter()
        self.assertIsInstance(adapter, LocalFileStorageAdapter)

    @patch("backend.infrastructure.storage.factory.Config.STORAGE_BACKEND", "s3")
    @patch("backend.infrastructure.storage.factory.S3StorageAdapter.from_config")
    def test_factory_returns_s3_adapter(self, from_config_mock):
        from_config_mock.return_value = Mock(spec=S3StorageAdapter)
        adapter = create_storage_adapter()
        self.assertIs(adapter, from_config_mock.return_value)

    @patch("backend.infrastructure.storage.factory.Config.STORAGE_BACKEND", "unknown")
    def test_factory_raises_for_unsupported_backend(self):
        with self.assertRaises(StorageError):
            create_storage_adapter()


if __name__ == "__main__":
    unittest.main()
