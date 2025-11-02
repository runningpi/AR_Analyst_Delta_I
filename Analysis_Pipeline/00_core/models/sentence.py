"""Sentence models for the pipeline."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    """Classification of claim type (verifiable vs non-verifiable)."""
    ASSERTION = "assertion"
    HYPOTHESIS = "hypothesis"
    OTHER = "other"


class SubjectScope(str, Enum):
    """Classification of subject scope."""
    COMPANY = "company"
    MARKET = "market"
    OTHER = "other"


class SentenceType(str, Enum):
    """Classification of sentence content type."""
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    OTHER = "other"


class ContentRelevance(str, Enum):
    """Classification of whether content is relevant to the company analysis."""
    COMPANY_RELEVANT = "company_relevant"
    TEMPLATE_BOILERPLATE = "template_boilerplate"
    OTHER = "other"


class InformationSource(str, Enum):
    """Classification of whether information comes from text or table in the analyst paper."""
    TEXT = "text"
    TABLE = "table"


class Sentence(BaseModel):
    """A single sentence extracted from the analyst report."""
    
    text: str = Field(..., description="The sentence text")
    section: str = Field(..., description="Section this sentence belongs to")
    index: int = Field(..., description="Index within the section")
    
    class Config:
        frozen = False


class ClassifiedSentence(Sentence):
    """A sentence with classification and confidence scores."""
    
    claim_type: ClaimType = Field(..., description="Classification of claim type (assertion or hypothesis)")
    subject_scope: SubjectScope = Field(..., description="Classification of subject scope (company, market, or other)")
    sentence_type: SentenceType = Field(..., description="Classification of the sentence content type")
    content_relevance: ContentRelevance = Field(..., description="Whether content is relevant to company analysis or is template/boilerplate")
    information_source: InformationSource = Field(..., description="Whether information comes from text or table in the analyst paper")
    claim_type_confidence: float = Field(..., description="Confidence score for claim type classification (0.0-1.0)")
    subject_scope_confidence: float = Field(..., description="Confidence score for subject scope classification (0.0-1.0)")
    sentence_type_confidence: float = Field(..., description="Confidence score for sentence type classification (0.0-1.0)")
    content_relevance_confidence: float = Field(..., description="Confidence score for content relevance classification (0.0-1.0)")
    information_source_confidence: float = Field(..., description="Confidence score for information source classification (0.0-1.0)")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sentence": self.text,
            "claim_type": self.claim_type.value,
            "subject_scope": self.subject_scope.value,
            "sentence_type": self.sentence_type.value,
            "content_relevance": self.content_relevance.value,
            "information_source": self.information_source.value,
            "claim_type_confidence": self.claim_type_confidence,
            "subject_scope_confidence": self.subject_scope_confidence,
            "sentence_type_confidence": self.sentence_type_confidence,
            "content_relevance_confidence": self.content_relevance_confidence,
            "information_source_confidence": self.information_source_confidence,
            "section": self.section,
            "index": self.index,
        }

