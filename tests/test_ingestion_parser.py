import io
import unittest
import zipfile

from backend.core.exceptions import ParsingError
from backend.ingestion.chunker import chunk_blocks
from backend.ingestion.parser import parse_document


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>" for text in paragraphs)
        + "</w:body>"
        "</w:document>"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _make_docx_xml_bytes(document_xml: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


class ParserTestCase(unittest.TestCase):
    def test_parse_plain_text(self):
        blocks = parse_document("sample.txt", "text/plain", b" hello\nworld ")
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["text"], "hello world")
        self.assertEqual(blocks[0]["block_type"], "paragraph")

    def test_parse_docx(self):
        content = _make_docx_bytes(["Первый абзац", "Второй абзац"])
        blocks = parse_document(
            "sample.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content,
        )
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0]["text"], "Первый абзац")
        self.assertEqual(blocks[1]["text"], "Второй абзац")
        self.assertEqual(blocks[0]["heading_path"], [])

    def test_parse_docx_extracts_headings_and_tables(self):
        content = _make_docx_xml_bytes(
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            "<w:body>"
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Документ</w:t></w:r></w:p>'
            '<w:p><w:r><w:t>Вводный   текст</w:t></w:r></w:p>'
            "<w:tbl>"
            "<w:tr>"
            "<w:tc><w:p><w:r><w:t>A1</w:t></w:r></w:p></w:tc>"
            "<w:tc><w:p><w:r><w:t>B1</w:t></w:r></w:p></w:tc>"
            "</w:tr>"
            "</w:tbl>"
            "</w:body>"
            "</w:document>"
        )
        blocks = parse_document(
            "sample.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            content,
        )
        self.assertEqual(blocks[0]["text"], "Документ")
        self.assertEqual(blocks[0]["block_type"], "heading")
        self.assertEqual(blocks[0]["heading_path"], ["Документ"])
        self.assertEqual(blocks[1]["text"], "Вводный текст")
        self.assertEqual(blocks[1]["section"], "Документ")
        self.assertEqual(blocks[1]["heading_path"], ["Документ"])
        self.assertEqual(blocks[2]["text"], "A1 | B1")
        self.assertEqual(blocks[2]["section"], "Документ")
        self.assertEqual(blocks[2]["block_type"], "table_row")
        self.assertTrue(blocks[2]["is_table_like"])

    def test_parse_pdf_without_dependency_raises_parsing_error(self):
        with self.assertRaises(ParsingError) as context:
            parse_document("sample.pdf", "application/pdf", b"%PDF-1.7")
        self.assertEqual(context.exception.code, "parsing_failed")


class ChunkerTestCase(unittest.TestCase):
    def test_chunk_blocks_splits_long_text(self):
        blocks = [{"text": " ".join(["word"] * 250), "page": 1, "section": None}]
        chunks = chunk_blocks(blocks, chunk_size_tokens=100, chunk_overlap_tokens=10)
        self.assertGreaterEqual(len(chunks), 3)
        self.assertEqual(chunks[0]["page"], 1)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["token_count"], 100)
        self.assertIn("block_types", chunks[0])

    def test_chunk_blocks_ignores_empty_items(self):
        chunks = chunk_blocks(
            [{"text": "   "}, {"text": "ok"}],
            chunk_size_tokens=100,
            chunk_overlap_tokens=10,
        )
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["content"], "ok")

    def test_chunk_blocks_keeps_heading_with_following_content(self):
        chunks = chunk_blocks(
            [
                {"text": "Раздел 1", "block_type": "heading", "heading_path": ["Раздел 1"], "page": 1, "section": "Раздел 1"},
                {"text": "Основной технический текст", "block_type": "paragraph", "heading_path": ["Раздел 1"], "page": 1, "section": "Раздел 1"},
            ],
            chunk_size_tokens=100,
            chunk_overlap_tokens=10,
        )
        self.assertEqual(len(chunks), 1)
        self.assertIn("Раздел 1", chunks[0]["content"])
        self.assertIn("Основной технический текст", chunks[0]["content"])

    def test_chunk_blocks_separates_table_rows(self):
        chunks = chunk_blocks(
            [
                {"text": "A1 | B1", "block_type": "table_row", "heading_path": [], "page": 1, "section": "T"},
                {"text": "A2 | B2", "block_type": "table_row", "heading_path": [], "page": 1, "section": "T"},
            ],
            chunk_size_tokens=100,
            chunk_overlap_tokens=10,
        )
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["block_type"], "table_row")

    def test_chunk_blocks_validates_overlap(self):
        with self.assertRaises(ValueError):
            chunk_blocks([{"text": "one two"}], chunk_size_tokens=2, chunk_overlap_tokens=2)


if __name__ == "__main__":
    unittest.main()
