"""
Evaluation utilities using LLM to assess evidence support.

This module provides utilities for evaluating whether knowledge base
evidence supports analyst report sentences.
"""

import json
import logging
from typing import List, Dict, Any
from openai import OpenAI

from models.evaluation import EvaluationLabel, EvaluationResult, SentenceEvaluation
from RAG_and_knowledgebase.matching_utils import EvidenceFormatter

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for evaluating sentence support using LLM."""
    
    SYSTEM_PROMPT = """You are an expert financial analyst.
Evaluate whether the provided Knowledge Base evidence supports the snippet.
Return a JSON object with two keys:
- evaluation: one of [Supported, Partially Supported, Not Supported, Contradicted, No Evidence]
- reason: a short explanation.

Definitions:
- Supported: The evidence fully backs the claim in the snippet
- Partially Supported: The evidence partially backs the claim, but some aspects are missing
- Not Supported: The evidence doesn't back the claim
- Contradicted: The evidence directly contradicts the claim
- No Evidence: No relevant evidence was found in the knowledge base
"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the evaluation service.
        
        Args:
            model: OpenAI model to use for evaluation
        """
        self.client = OpenAI()
        self.model = model
        self.evidence_formatter = EvidenceFormatter()
        logger.info(f"EvaluationService initialized with model={model}")
    
    def evaluate_sentence(
        self,
        sentence: str,
        evidence_texts: List[str],
    ) -> EvaluationResult:
        """
        Evaluate a single sentence against evidence.
        
        Args:
            sentence: Sentence to evaluate
            evidence_texts: List of evidence text strings
            
        Returns:
            EvaluationResult with label and reason
        """
        # Check if evidence exists
        if not self.evidence_formatter.has_evidence(evidence_texts):
            return EvaluationResult(
                evaluation=EvaluationLabel.NO_EVIDENCE,
                reason="No evidence found in knowledge base"
            )
        
        # Format evidence
        evidence_combined = self.evidence_formatter.format_evidence(evidence_texts)
        
        # Create prompt
        user_prompt = f"""Snippet:
{sentence}

Evidence from Knowledge Base:
{evidence_combined}
"""
        
        try:
            # Call LLM
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            
            raw_response = response.choices[0].message.content.strip()
            parsed = json.loads(raw_response)
            
            result = EvaluationResult.from_llm_response(parsed)
            logger.debug(f"Evaluated sentence: {result.evaluation.value}")
            
            return result
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            return EvaluationResult(
                evaluation=EvaluationLabel.UNKNOWN,
                reason=f"Evaluation error: {str(e)}"
            )
    
    def evaluate_query_results(
        self,
        query_results: Dict[str, List[Dict[str, Any]]],
        show_progress: bool = True,
    ) -> Dict[str, List[SentenceEvaluation]]:
        """
        Evaluate all query results.
        
        Args:
            query_results: Dictionary mapping sections to query results
            show_progress: Whether to log progress
            
        Returns:
            Dictionary mapping sections to sentence evaluations
        """
        logger.info(f"Starting evaluation for {len(query_results)} sections")
        
        evaluations = {}
        total_sentences = 0
        
        for section_name, items in query_results.items():
            section_evals = []
            
            logger.info(f"Evaluating {len(items)} sentences in section: {section_name}")
            
            for item in items:
                sentence = item.get("sentence", "")
                source = item.get("source", "unknown")
                evidence = item.get("evidence", [])
                
                # Evaluate
                eval_result = self.evaluate_sentence(sentence, evidence)
                
                # Create sentence evaluation
                sentence_eval = SentenceEvaluation(
                    sentence=sentence,
                    section=section_name,
                    source=source,
                    evidence=evidence,
                    evaluation=eval_result.evaluation,
                    reason=eval_result.reason,
                )
                
                section_evals.append(sentence_eval)
                total_sentences += 1
                
                if show_progress:
                    logger.debug(
                        f"[{section_name}] {sentence[:50]}... "
                        f"→ {eval_result.evaluation.value}"
                    )
            
            evaluations[section_name] = section_evals
            logger.info(f"Completed evaluation for section: {section_name}")
        
        logger.info(f"Evaluation complete. Total sentences evaluated: {total_sentences}")
        return evaluations
    
    def evaluations_to_dict(
        self,
        evaluations: Dict[str, List[SentenceEvaluation]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Convert evaluations to dictionary format for JSON serialization.
        
        Args:
            evaluations: Dictionary of sentence evaluations
            
        Returns:
            Dictionary format suitable for JSON
        """
        return {
            section: [eval.to_dict() for eval in evals]
            for section, evals in evaluations.items()
        }

