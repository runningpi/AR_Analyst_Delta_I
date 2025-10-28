"""Decomposition AR module for text extraction and parsing."""

from .ocr_huggingface_utils import HuggingFaceDeepseekOCRParser, TextCleaner, SentenceSplitter, extract_sentences_per_section

__all__ = [
    "HuggingFaceDeepseekOCRParser",
    "TextCleaner",
    "SentenceSplitter",
    "extract_sentences_per_section",
]

