import io
import unittest
import zipfile

from backend.ingestion.file_types import resolve_upload_mime_type


def _make_docx_bytes(text: str) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


class FileTypesTestCase(unittest.TestCase):
    def test_resolve_text_plain(self):
        mime = resolve_upload_mime_type("sample.txt", "text/plain", b"hello world")
        self.assertEqual(mime, "text/plain")

    def test_resolve_pdf_with_octet_stream(self):
        mime = resolve_upload_mime_type("sample.pdf", "application/octet-stream", b"%PDF-1.7\nbinary")
        self.assertEqual(mime, "application/pdf")

    def test_rejects_spoofed_pdf_with_text_content(self):
        mime = resolve_upload_mime_type("sample.pdf", "application/pdf", b"just plain text")
        self.assertIsNone(mime)

    def test_resolve_docx(self):
        mime = resolve_upload_mime_type(
            "sample.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            _make_docx_bytes("hello"),
        )
        self.assertEqual(mime, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")


if __name__ == "__main__":
    unittest.main()
