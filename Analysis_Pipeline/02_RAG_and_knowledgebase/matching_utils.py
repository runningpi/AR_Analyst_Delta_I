"""
Sentence matching utilities for RAG operations.

This module provides functionality to match analyst report sentences
against company documents using the knowledge base.
"""

import logging
from typing import Dict, List, Any, Optional
from tqdm import tqdm

from .DS_RAG_utils import KnowledgeBaseManager

logger = logging.getLogger(__name__)


class EvidenceFormatter:
    """
    Formats evidence for evaluation and display.
    
    This class handles:
    - Evidence text extraction and formatting
    - Evidence validation
    - Text preprocessing for evaluation
    """
    
    def __init__(self):
        """Initialize the evidence formatter."""
        logger.info("EvidenceFormatter initialized")
    
    def has_evidence(self, evidence_texts: List[str]) -> bool:
        """
        Check if there is meaningful evidence.
        
        Args:
            evidence_texts: List of evidence text strings
            
        Returns:
            True if there is meaningful evidence
        """
        if not evidence_texts:
            return False
        
        # Check if any evidence text is meaningful (not empty, not just whitespace)
        for text in evidence_texts:
            if text and text.strip():
                return True
        
        return False
    
    def format_evidence(self, evidence_texts: List[str], max_length: int = 2000) -> str:
        """
        Format evidence texts for evaluation.
        
        Args:
            evidence_texts: List of evidence text strings
            max_length: Maximum length of formatted evidence
            
        Returns:
            Formatted evidence string
        """
        if not self.has_evidence(evidence_texts):
            return "No evidence found."
        
        # Filter out empty evidence
        valid_evidence = [text.strip() for text in evidence_texts if text and text.strip()]
        
        if not valid_evidence:
            return "No evidence found."
        
        # Combine evidence with separators
        formatted = "\n\n--- Evidence ---\n".join(valid_evidence)
        
        # Truncate if too long
        if len(formatted) > max_length:
            formatted = formatted[:max_length] + "... [truncated]"
        
        return formatted
    
    def extract_evidence_content(self, evidence_list: List[Dict[str, Any]]) -> List[str]:
        """
        Extract content from evidence list.
        
        Args:
            evidence_list: List of evidence dictionaries
            
        Returns:
            List of evidence content strings
        """
        if not evidence_list:
            return []
        
        content_list = []
        for evidence in evidence_list:
            content = evidence.get('content', '')
            if content and content.strip():
                content_list.append(content.strip())
        
        return content_list


class SentenceMatcher:
    """
    Matches sentences from analyst reports against company documents.
    
    This class handles:
    - Querying the knowledge base for each sentence
    - Ranking and filtering results
    - Formatting evidence for evaluation
    """
    
    def __init__(
        self,
        kb_manager: KnowledgeBaseManager,
        top_k: int = 5
    ):
        """
        Initialize the sentence matcher.
        
        Args:
            kb_manager: Knowledge base manager instance
            top_k: Number of top results to return for each query
        """
        self.kb_manager = kb_manager
        self.top_k = top_k
        
        logger.info(f"SentenceMatcher initialized with top_k={top_k}")
    
    def match_sentence(
        self,
        sentence: str,
        sentence_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Match a single sentence against the knowledge base.
        
        Args:
            sentence: Sentence text to match
            sentence_id: Optional identifier for the sentence
            
        Returns:
            List of evidence results
        """
        try:
            # Query the knowledge base
            results = self.kb_manager.query(sentence, top_k=self.top_k)
            
            # Format results as evidence
            evidence = []
            for i, result in enumerate(results):
                evidence_item = {
                    "rank": i + 1,
                    "score": float(result.get('score', 0.0)),
                    "content": result.get('content', ''),
                    "doc_id": result.get('doc_id', ''),
                    "chunk_start": result.get('chunk_start', 0),
                    "chunk_end": result.get('chunk_end', 0),
                    "metadata": {
                        "sentence_id": sentence_id,
                        "query_text": sentence
                    }
                }
                evidence.append(evidence_item)
            
            logger.debug(f"Found {len(evidence)} evidence items for sentence")
            return evidence
            
        except Exception as e:
            logger.error(f"Failed to match sentence: {e}")
            return []
    
    def match_classified_snippets(
        self,
        classified_snippets: Dict[str, List[Dict[str, str]]],
        show_progress: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Match all classified snippets against the knowledge base.
        
        Args:
            classified_snippets: Dictionary mapping sections to classified snippets
            show_progress: Whether to show progress bar
            
        Returns:
            Dictionary mapping sections to query results with evidence in the format:
            {
                "ADVANCED MICRO DEVICES INC": [
                    {
                        "snippet": "snippet text",
                        "source": "primary",
                        "sentence_type": "qualitative",
                        "source_confidence": 0.9,
                        "sentence_type_confidence": 0.8,
                        "evidence": [
                            {
                                "content": "evidence content",
                                "score": 0.85,
                                "doc_id": "document_id",
                                "rank": 1
                            }
                        ]
                    }
                ]
            }
        """
        logger.info("Starting snippet matching against knowledge base")
        
        query_results = {}
        total_snippets = sum(len(snippets) for snippets in classified_snippets.values())
        
        logger.info(f"Processing {total_snippets} snippets across {len(classified_snippets)} sections")
        
        # Create progress bar if requested
        if show_progress:
            pbar = tqdm(total=total_snippets, desc="Matching snippets")
        
        try:
            for section_name, snippets in classified_snippets.items():
                logger.info(f"Processing section: {section_name} ({len(snippets)} snippets)")
                
                section_results = []
                
                for i, snippet_data in enumerate(snippets):
                    snippet_text = snippet_data.get('snippet', '')
                    snippet_id = f"{section_name}_{i}"
                    
                    # Match snippet against KB
                    evidence = self.match_sentence(snippet_text, snippet_id)
                    
                    # Format evidence for output (top 5 results)
                    formatted_evidence = self._format_evidence_for_output(evidence, max_evidence=5)
                    
                    # Create result in the required format, preserving all classification data
                    result = {
                        "snippet": snippet_text,
                        "source": snippet_data.get('source', 'unknown'),
                        "sentence_type": snippet_data.get('sentence_type', 'qualitative'),
                        "source_confidence": snippet_data.get('source_confidence', 0.5),
                        "sentence_type_confidence": snippet_data.get('sentence_type_confidence', 0.5),
                        "evidence": formatted_evidence
                    }
                    
                    section_results.append(result)
                    
                    if show_progress:
                        pbar.update(1)
                
                query_results[section_name] = section_results
                logger.info(f"Completed section: {section_name}")
            
            if show_progress:
                pbar.close()
            
            logger.info("Snippet matching completed successfully")
            return query_results
            
        except Exception as e:
            logger.error(f"Snippet matching failed: {e}")
            if show_progress:
                pbar.close()
            raise
    
    def _format_evidence_for_output(
        self,
        evidence: List[Dict[str, Any]],
        max_evidence: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Format evidence for output in the required JSON format.
        
        Args:
            evidence: List of evidence items
            max_evidence: Maximum number of evidence items to include
            
        Returns:
            Formatted evidence list
        """
        if not evidence:
            return []
        
        # Sort by score (descending) and take top results
        sorted_evidence = sorted(evidence, key=lambda x: x.get('score', 0), reverse=True)
        top_evidence = sorted_evidence[:max_evidence]
        
        # Format for output
        formatted_evidence = []
        for item in top_evidence:
            formatted_item = {
                "content": item.get('content', ''),
                "score": item.get('score', 0.0),
                "doc_id": item.get('doc_id', ''),
                "rank": item.get('rank', 0)
            }
            formatted_evidence.append(formatted_item)
        
        return formatted_evidence
    
    def get_matching_statistics(
        self,
        query_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Get statistics about the matching results.
        
        Args:
            query_results: Results from match_classified_sentences
            
        Returns:
            Dictionary with matching statistics
        """
        total_sentences = sum(len(sentences) for sentences in query_results.values())
        total_evidence = 0
        evidence_distribution = {}
        
        for section_name, sentences in query_results.items():
            for sentence_data in sentences:
                evidence_count = len(sentence_data.get('evidence', []))
                total_evidence += evidence_count
                evidence_distribution[evidence_count] = evidence_distribution.get(evidence_count, 0) + 1
        
        avg_evidence_per_sentence = total_evidence / total_sentences if total_sentences > 0 else 0
        
        return {
            "total_sentences": total_sentences,
            "total_sections": len(query_results),
            "total_evidence": total_evidence,
            "avg_evidence_per_sentence": avg_evidence_per_sentence,
            "evidence_distribution": evidence_distribution
        }
