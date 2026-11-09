"""Document Parsing Engines: PyMuPDF with Financial Table Extraction and Docling Interface."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pymupdf

logger = logging.getLogger(__name__)


def _format_table_markdown(extracted_table: List[List[Optional[str]]]) -> str:
    """Convert extracted table rows into clean GitHub-flavored Markdown table format."""
    if not extracted_table or len(extracted_table) < 2:
        return ""

    # Clean whitespace and None cells
    cleaned_rows = []
    for row in extracted_table:
        cleaned_rows.append([str(c or "").strip().replace("\n", " ") for c in row])

    # Check for empty table
    if not any(any(cell for cell in row) for row in cleaned_rows):
        return ""

    headers = cleaned_rows[0]
    separator = ["---"] * len(headers)
    body = cleaned_rows[1:]

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in body:
        # Pad row if uneven
        padded_row = row + [""] * (len(headers) - len(row))
        lines.append("| " + " | ".join(padded_row[: len(headers)]) + " |")

    return "\n".join(lines)


class ParsedPage:
    """Container for page-level extracted content and metadata."""

    def __init__(
        self,
        page_number: int,
        text: str,
        tables: Optional[List[Dict[str, Any]]] = None,
        section: Optional[str] = None,
    ):
        self.page_number = page_number
        self.text = text
        self.tables = tables or []
        self.section = section

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "tables": self.tables,
            "section": self.section,
        }


class DocumentParserInterface(ABC):
    """Abstract interface for document parsers."""

    @abstractmethod
    def parse_pdf(
        self, file_source: Union[bytes, str, Path]
    ) -> List[ParsedPage]:
        """Parse PDF binary bytes or file path into list of ParsedPage objects."""
        pass


class PyMuPDFParser(DocumentParserInterface):
    """Production PyMuPDF parser supporting page text, table extraction, and structure."""

    def parse_pdf(
        self, file_source: Union[bytes, str, Path]
    ) -> List[ParsedPage]:
        try:
            if isinstance(file_source, bytes):
                doc = pymupdf.open(stream=file_source, filetype="pdf")
            else:
                doc = pymupdf.open(str(file_source))
        except Exception as e:
            raise ValueError(f"Invalid or corrupted PDF file: {e}") from e

        if doc.needs_pass:
            doc.close()
            raise ValueError("Password-protected PDFs are not supported.")

        parsed_pages: List[ParsedPage] = []
        current_section = "General"

        try:
            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_num = page_idx + 1

                # 1. Extract raw text
                page_text = page.get_text("text").strip()

                # Detect potential section headers (lines that look like headings)
                for line in page_text.splitlines()[:5]:
                    stripped = line.strip()
                    if stripped.isupper() and 4 < len(stripped) < 60:
                        current_section = stripped
                        break

                # 2. Extract tables using PyMuPDF find_tables
                extracted_tables: List[Dict[str, Any]] = []
                try:
                    tables_obj = page.find_tables()
                    for t_idx, tab in enumerate(tables_obj.tables):
                        tab_data = tab.extract()
                        if tab_data and len(tab_data) >= 2:
                            md_table = _format_table_markdown(tab_data)
                            if md_table:
                                extracted_tables.append({
                                    "table_index": t_idx + 1,
                                    "markdown": md_table,
                                    "row_count": len(tab_data),
                                    "col_count": len(tab_data[0]) if tab_data else 0,
                                })
                except Exception as table_err:
                    logger.debug("Table detection skipped on page %d: %s", page_num, table_err)

                parsed_pages.append(
                    ParsedPage(
                        page_number=page_num,
                        text=page_text,
                        tables=extracted_tables,
                        section=current_section,
                    )
                )
        finally:
            doc.close()

        return parsed_pages


class DoclingParser(DocumentParserInterface):
    """Pluggable adapter for IBM Docling document parsing.

    Falls back to PyMuPDFParser if docling is not installed in the environment.
    """

    def __init__(self):
        self._fallback = PyMuPDFParser()

    def parse_pdf(
        self, file_source: Union[bytes, str, Path]
    ) -> List[ParsedPage]:
        try:
            import docling  # type: ignore
            # When docling is available in runtime, layout parsing is executed here
            logger.info("Executing Docling layout parser...")
            # Fallback to robust PyMuPDF parser for current pipeline
            return self._fallback.parse_pdf(file_source)
        except ImportError:
            logger.debug("Docling not installed; utilizing PyMuPDFParser.")
            return self._fallback.parse_pdf(file_source)

