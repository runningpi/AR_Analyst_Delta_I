"""
Evaluation utilities using LLM to assess evidence support.

This module provides utilities for evaluating whether knowledge base
evidence supports analyst report sentences.
"""

import json
import logging
from typing import List, Dict, Any
from openai import OpenAI

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# Import with proper module paths
core_eval_models = __import__('00_core.models.evaluation', fromlist=['EvaluationLabel', 'EvaluationResult', 'SentenceEvaluation'])
EvaluationLabel = core_eval_models.EvaluationLabel
EvaluationResult = core_eval_models.EvaluationResult
SentenceEvaluation = core_eval_models.SentenceEvaluation

rag_matching = __import__('02_RAG_and_knowledgebase.matching_utils', fromlist=['EvidenceFormatter'])
EvidenceFormatter = rag_matching.EvidenceFormatter

logger = logging.getLogger(__name__)


class EvaluationService:
    """Service for evaluating sentence support using LLM."""
    
    SYSTEM_PROMPT = """You are an expert financial analyst.
Evaluate whether the provided Knowledge Base evidence supports the snippet.
Return a JSON object with the following keys:
- evaluation: one of [Supported, Partially Supported, Contradicted, Not Supported, No Evidence]
- reason: a short explanation
- support_score: a numeric score from 0.0 to 1.0 indicating the degree of support
  * 0.9-1.0: Fully supported (use "Supported" label)
  * 0.5-0.89: Partially supported (use "Partially Supported" label)
  * 0.0-0.49: Not supported (use "Not Supported" label)
  * -1.0: Contradicted (use "Contradicted" label)
  * 0.0: No evidence (use "No Evidence" label)

Definitions:
- Supported (0.9-1.0): The evidence fully backs the claim in the snippet
- Partially Supported (0.5-0.89): The evidence partially backs the claim, but some aspects are missing
- Not Supported (0.0-0.49): The evidence does not support the claim
- Contradicted (-1.0): The evidence directly contradicts the claim
- No Evidence (0.0): No relevant evidence was found in the knowledge base

Be precise with your support_score. A score of 0.9 or higher should be directly recognized as "Supported".
"""
    
    DELTA_ANALYSIS_PROMPT = """You are an expert financial analyst.
Analyze the delta between the snippet claim and the evidence for a Partially Supported evaluation.

Provide a detailed analysis of:
1. What aspects of the claim ARE supported by the evidence
2. What aspects of the claim are MISSING from the evidence
3. What differences exist (if any) - e.g., different numbers, timeframes, or interpretations
4. Quantify differences where possible (e.g., "Evidence shows 10% growth, snippet claims 15%")

Return a JSON object with:
- delta_analysis: A detailed explanation of what's missing or different
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
        section: str = None,
    ) -> EvaluationResult:
        """
        Evaluate a single sentence against evidence.
        
        Args:
            sentence: Sentence to evaluate
            evidence_texts: List of evidence text strings
            section: Section name where the sentence appears (for context)
            
        Returns:
            EvaluationResult with label, reason, and support_score
        """
        # Check if evidence exists
        if not self.evidence_formatter.has_evidence(evidence_texts):
            return EvaluationResult(
                evaluation=EvaluationLabel.NO_EVIDENCE,
                reason="No evidence found in knowledge base",
                support_score=0.0,
                delta_analysis=None
            )
        
        # Format evidence
        evidence_combined = self.evidence_formatter.format_evidence(evidence_texts)
        
        # Create prompt with section context
        section_context = f"\n\nContext: This snippet appears in the '{section}' section of the analyst report." if section else ""
        
        user_prompt = f"""Snippet:
{sentence}{section_context}

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
            
            # Adjust evaluation label based on support_score if needed
            # If support_score >= 0.9, it should be "Supported"
            if result.support_score >= 0.9 and result.evaluation == EvaluationLabel.PARTIALLY_SUPPORTED:
                result.evaluation = EvaluationLabel.SUPPORTED
                logger.debug(f"Upgraded to Supported based on support_score {result.support_score}")
            
            logger.debug(f"Evaluated sentence: {result.evaluation.value} (score: {result.support_score:.2f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Evaluation failed: {e}", exc_info=True)
            return EvaluationResult(
                evaluation=EvaluationLabel.UNKNOWN,
                reason=f"Evaluation error: {str(e)}",
                support_score=0.0,
                delta_analysis=None
            )
    
    def evaluate_partially_supported_delta(
        self,
        sentence: str,
        evidence_texts: List[str],
        section: str = None,
    ) -> str:
        """
        Perform deep-dive delta analysis for Partially Supported items.
        
        Args:
            sentence: Sentence that was evaluated as Partially Supported
            evidence_texts: List of evidence text strings
            section: Section name where the sentence appears (for context)
            
        Returns:
            Detailed delta analysis string
        """
        # Format evidence
        evidence_combined = self.evidence_formatter.format_evidence(evidence_texts)
        
        # Create prompt with section context
        section_context = f"\n\nContext: This snippet appears in the '{section}' section of the analyst report." if section else ""
        
        user_prompt = f"""Snippet:
{sentence}{section_context}

Evidence from Knowledge Base:
{evidence_combined}

This snippet was evaluated as "Partially Supported". Provide a detailed delta analysis.
"""
        
        try:
            # Call LLM for delta analysis
            response = self.client.chat.completions.create(
                model=self.model,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": self.DELTA_ANALYSIS_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            
            raw_response = response.choices[0].message.content.strip()
            parsed = json.loads(raw_response)
            
            delta_analysis = parsed.get("delta_analysis", "Delta analysis not available")
            logger.debug(f"Generated delta analysis for Partially Supported item")
            
            return delta_analysis
            
        except Exception as e:
            logger.error(f"Delta analysis failed: {e}", exc_info=True)
            return f"Delta analysis error: {str(e)}"
    
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
                # Get snippet/sentence text - prefer "snippet" (used in query results) over "sentence"
                sentence = item.get("snippet", item.get("sentence", ""))
                claim_type = item.get("claim_type", "hypothesis")
                subject_scope = item.get("subject_scope", "company")
                sentence_type = item.get("sentence_type", "qualitative")
                content_relevance = item.get("content_relevance", "company_relevant")
                claim_type_confidence = float(item.get("claim_type_confidence", 0.5))
                subject_scope_confidence = float(item.get("subject_scope_confidence", 0.5))
                sentence_type_confidence = float(item.get("sentence_type_confidence", 0.5))
                content_relevance_confidence = float(item.get("content_relevance_confidence", 0.5))
                evidence = item.get("evidence", [])
                
                # Skip if sentence/snippet is empty
                if not sentence or not sentence.strip():
                    logger.warning(f"Skipping empty sentence/snippet in section {section_name}")
                    continue
                
                # Extract evidence content for evaluation
                evidence_content = self.evidence_formatter.extract_evidence_content(evidence)
                
                # Evaluate with section context
                eval_result = self.evaluate_sentence(sentence, evidence_content, section=section_name)
                
                # Perform delta analysis for Partially Supported items
                delta_analysis = None
                if eval_result.evaluation == EvaluationLabel.PARTIALLY_SUPPORTED:
                    delta_analysis = self.evaluate_partially_supported_delta(
                        sentence, evidence_content, section=section_name
                    )
                    eval_result.delta_analysis = delta_analysis
                
                # Extract evidence content strings for SentenceEvaluation model
                evidence_strings = []
                if evidence:
                    for ev in evidence:
                        if isinstance(ev, dict) and 'content' in ev:
                            evidence_strings.append(ev['content'])
                        elif isinstance(ev, str):
                            evidence_strings.append(ev)
                
                # Create sentence evaluation
                sentence_eval = SentenceEvaluation(
                    sentence=sentence,
                    section=section_name,
                    claim_type=claim_type,
                    subject_scope=subject_scope,
                    sentence_type=sentence_type,
                    content_relevance=content_relevance,
                    claim_type_confidence=claim_type_confidence,
                    subject_scope_confidence=subject_scope_confidence,
                    sentence_type_confidence=sentence_type_confidence,
                    content_relevance_confidence=content_relevance_confidence,
                    evidence=evidence_strings,
                    evaluation=eval_result.evaluation,
                    reason=eval_result.reason,
                    support_score=eval_result.support_score,
                    delta_analysis=eval_result.delta_analysis,
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

