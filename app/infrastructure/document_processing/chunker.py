"""Structure-Aware and Token-Aware Chunker for Financial Documents."""

import re
from typing import Any, Dict, List, Optional

from app.config import get_settings
from app.infrastructure.document_processing.parser import ParsedPage


def estimate_tokens(text: str) -> int:
    """Fast approximation of token count (~4 characters per token for English)."""
    return max(1, len(text) // 4)


class StructureAwareChunker:
    """Splits parsed pages into token-aware, metadata-rich semantic chunks."""

    def __init__(
        self,
        target_tokens: Optional[int] = None,
        overlap_tokens: Optional[int] = None,
    ):
        settings = get_settings()
        self.target_tokens = target_tokens or settings.chunk_target_tokens
        self.overlap_tokens = overlap_tokens or settings.chunk_overlap_tokens

        # Character equivalents
        self.target_chars = self.target_tokens * 4
        self.overlap_chars = self.overlap_tokens * 4

    def chunk_pages(
        self,
        pages: List[ParsedPage],
        document_id: str,
        filename: str,
    ) -> List[Dict[str, Any]]:
        """Split a list of ParsedPages into structured chunks."""
        all_chunks: List[Dict[str, Any]] = []
        global_chunk_idx = 1

        for page in pages:
            page_chunk_idx = 1

            # 1. First, process any extracted tables as dedicated tabular chunks
            for table_meta in page.tables:
                table_md = table_meta.get("markdown", "")
                if table_md.strip():
                    chunk_text = f"### Financial Table (Page {page.page_number})\n{table_md}"
                    all_chunks.append({
                        "chunk_id": f"{document_id}-{global_chunk_idx}",
                        "document_id": document_id,
                        "filename": filename,
                        "page_number": page.page_number,
                        "page_chunk_index": page_chunk_idx,
                        "section": page.section or "Financial Tables",
                        "is_table": True,
                        "text": chunk_text,
                        "token_count": estimate_tokens(chunk_text),
                    })
                    global_chunk_idx += 1
                    page_chunk_idx += 1

            # 2. Chunk page textual narrative
            text = page.text.strip()
            if not text:
                continue

            text_chunks = self._split_text(text)
            for chunk_str in text_chunks:
                all_chunks.append({
                    "chunk_id": f"{document_id}-{global_chunk_idx}",
                    "document_id": document_id,
                    "filename": filename,
                    "page_number": page.page_number,
                    "page_chunk_index": page_chunk_idx,
                    "section": page.section or "General Narrative",
                    "is_table": False,
                    "text": chunk_str,
                    "token_count": estimate_tokens(chunk_str),
                })
                global_chunk_idx += 1
                page_chunk_idx += 1

        return all_chunks

    def _split_text(self, text: str) -> List[str]:
        """Split continuous text into overlapping windows respecting sentence boundaries."""
        if len(text) <= self.target_chars:
            return [text]

        chunks: List[str] = []
        start = 0
        total_len = len(text)

        while start < total_len:
            end = min(start + self.target_chars, total_len)

            if end < total_len:
                # Seek cleanest break point: paragraph, newline, period, space
                boundary = -1
                for delim in ["\n\n", ".\n", ". ", "\n", " "]:
                    pos = text.rfind(delim, start + int(self.target_chars * 0.6), end)
                    if pos != -1:
                        boundary = pos + len(delim)
                        break

                if boundary != -1:
                    end = boundary

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= total_len:
                break

            # Calculate next start with overlap
            next_start = max(start + 1, end - self.overlap_chars)

            # Advance to word boundary
            while next_start < total_len and not text[next_start].isspace():
                next_start += 1
            while next_start < total_len and text[next_start].isspace():
                next_start += 1

            start = next_start

        return chunks

