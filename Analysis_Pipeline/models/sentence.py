"""Sentence models for the pipeline."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SentenceSource(str, Enum):
    """Classification of sentence source/type."""
    CORPORATE_INFORMATION = "corporate_information"
    MARKET_INFORMATION = "market_information"
    ANALYST_INTERPRETATION = "analyst_interpretation"
    OTHER = "other"


class Sentence(BaseModel):
    """A single sentence extracted from the analyst report."""
    
    text: str = Field(..., description="The sentence text")
    section: str = Field(..., description="Section this sentence belongs to")
    index: int = Field(..., description="Index within the section")
    
    class Config:
        frozen = False


class ClassifiedSentence(Sentence):
    """A sentence with source classification."""
    
    source: SentenceSource = Field(..., description="Classification of the sentence source")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sentence": self.text,
            "source": self.source.value,
            "section": self.section,
            "index": self.index,
        }

