"""Evaluation models for the pipeline."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EvaluationLabel(str, Enum):
    """Evaluation labels for sentence support."""
    SUPPORTED = "Supported"
    PARTIALLY_SUPPORTED = "Partially Supported"
    NOT_SUPPORTED = "Not Supported"
    CONTRADICTED = "Contradicted"
    NO_EVIDENCE = "No Evidence"
    UNKNOWN = "Unknown"


class EvaluationResult(BaseModel):
    """Result from LLM evaluation of a sentence."""
    
    evaluation: EvaluationLabel = Field(..., description="Evaluation label")
    reason: str = Field(..., description="Explanation for the evaluation")
    
    @classmethod
    def from_llm_response(cls, response_dict: dict) -> "EvaluationResult":
        """Create from LLM JSON response."""
        eval_str = response_dict.get("evaluation", "Unknown")
        
        # Map string to enum
        try:
            eval_label = EvaluationLabel(eval_str)
        except ValueError:
            eval_label = EvaluationLabel.UNKNOWN
        
        return cls(
            evaluation=eval_label,
            reason=response_dict.get("reason", "")
        )


class SentenceEvaluation(BaseModel):
    """Complete evaluation of a sentence including evidence and assessment."""
    
    sentence: str = Field(..., description="The sentence being evaluated")
    section: str = Field(..., description="Section the sentence belongs to")
    claim_type: str = Field(..., description="Claim type classification (assertion or hypothesis)")
    subject_scope: str = Field(..., description="Subject scope classification (company, market, or other)")
    sentence_type: str = Field(..., description="Sentence type classification")
    content_relevance: str = Field(..., description="Content relevance classification (company_relevant or template_boilerplate)")
    claim_type_confidence: float = Field(..., description="Confidence score for claim type classification (0.0-1.0)")
    subject_scope_confidence: float = Field(..., description="Confidence score for subject scope classification (0.0-1.0)")
    sentence_type_confidence: float = Field(..., description="Confidence score for sentence type classification (0.0-1.0)")
    content_relevance_confidence: float = Field(..., description="Confidence score for content relevance classification (0.0-1.0)")
    evidence: List[str] = Field(default_factory=list, description="Evidence texts from KB")
    evaluation: EvaluationLabel = Field(..., description="Evaluation label")
    reason: str = Field(..., description="Explanation for the evaluation")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        # Handle both enum and string values (Pydantic's use_enum_values may convert to string)
        eval_value = self.evaluation.value if isinstance(self.evaluation, EvaluationLabel) else self.evaluation
        return {
            "sentence": self.sentence,
            "section": self.section,
            "claim_type": self.claim_type,
            "subject_scope": self.subject_scope,
            "sentence_type": self.sentence_type,
            "content_relevance": self.content_relevance,
            "claim_type_confidence": self.claim_type_confidence,
            "subject_scope_confidence": self.subject_scope_confidence,
            "sentence_type_confidence": self.sentence_type_confidence,
            "content_relevance_confidence": self.content_relevance_confidence,
            "evidence": self.evidence,
            "evaluation": eval_value,
            "reason": self.reason,
        }
    
    class Config:
        use_enum_values = True

