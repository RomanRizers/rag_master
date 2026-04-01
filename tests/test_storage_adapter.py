import tempfile
import unittest

from backend.core.exceptions import StorageError
from backend.infrastructure.storage.local import LocalFileStorageAdapter


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


if __name__ == "__main__":
    unittest.main()
