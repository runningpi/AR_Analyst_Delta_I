"""Decomposition AR module for text extraction and parsing."""

from .ocr_docling_utils import DoclingParser, TextCleaner, SentenceSplitter, extract_sentences_per_section

__all__ = [
    "DoclingParser",
    "TextCleaner",
    "SentenceSplitter",
    "extract_sentences_per_section",
]

