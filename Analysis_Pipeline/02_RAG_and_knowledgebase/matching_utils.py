"""
Matching utilities for querying sentences against the knowledge base.

This module provides utilities for matching analyst report sentences
against company document knowledge base and retrieving evidence.
"""

import logging
from typing import List, Dict, Any
from tqdm import tqdm

from .DS_RAG_utils import KnowledgeBaseManager, segments_to_texts

logger = logging.getLogger(__name__)


class SentenceMatcher:
    """Match sentences against knowledge base to find supporting evidence."""
    
    def __init__(self, kb_manager: KnowledgeBaseManager, top_k: int = 5):
        """
        Initialize the sentence matcher.
        
        Args:
            kb_manager: Knowledge base manager instance
            top_k: Number of top results to retrieve per query
        """
        self.kb_manager = kb_manager
        self.top_k = top_k
        logger.info(f"SentenceMatcher initialized with top_k={top_k}")
    
    def match_sentence(self, sentence: str) -> List[str]:
        """
        Match a single sentence against the knowledge base.
        
        Args:
            sentence: Sentence to match
            
        Returns:
            List of evidence text strings
        """
        if not sentence or not sentence.strip():
            return []
        
        results = self.kb_manager.query(sentence, top_k=self.top_k)
        evidence_texts = segments_to_texts(results)
        
        return evidence_texts
    
    def match_classified_sentences(
        self,
        classified_data: Dict[str, List[Dict[str, str]]],
        show_progress: bool = True,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Match all classified sentences against the knowledge base.
        
        Args:
            classified_data: Dictionary mapping sections to classified sentences
            show_progress: Whether to show progress bar
            
        Returns:
            Dictionary mapping sections to query results with evidence
        """
        logger.info(f"Starting matching for {len(classified_data)} sections")
        
        query_results = {}
        total_sentences = 0
        
        for section_name, items in classified_data.items():
            query_results[section_name] = []
            
            # Setup progress bar
            iterator = items
            if show_progress:
                iterator = tqdm(
                    items,
                    desc=f"Matching {section_name}",
                    unit="sent",
                )
            
            for item in iterator:
                sentence = item.get("sentence", "").strip()
                
                if not sentence:
                    continue
                
                # Query the knowledge base
                evidence = self.match_sentence(sentence)
                
                # Store results
                result = {
                    "sentence": sentence,
                    "source": item.get("source"),
                    "evidence": evidence,
                }
                
                query_results[section_name].append(result)
                total_sentences += 1
            
            logger.debug(f"Completed matching for section: {section_name}")
        
        logger.info(f"Matching complete. Total sentences matched: {total_sentences}")
        return query_results
    
    def match_sentences_flat(
        self,
        sentences: List[str],
        show_progress: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Match a flat list of sentences.
        
        Args:
            sentences: List of sentences to match
            show_progress: Whether to show progress bar
            
        Returns:
            List of results with sentence and evidence
        """
        results = []
        
        iterator = sentences
        if show_progress:
            iterator = tqdm(sentences, desc="Matching sentences", unit="sent")
        
        for sentence in iterator:
            evidence = self.match_sentence(sentence)
            results.append({
                "sentence": sentence,
                "evidence": evidence,
            })
        
        return results


class EvidenceFormatter:
    """Format evidence texts for LLM evaluation."""
    
    @staticmethod
    def format_evidence(evidence_texts: List[str], max_items: int = 5) -> str:
        """
        Format evidence texts into a single string for LLM.
        
        Args:
            evidence_texts: List of evidence text strings
            max_items: Maximum number of evidence items to include
            
        Returns:
            Formatted evidence string
        """
        if not evidence_texts:
            return "No evidence found."
        
        # Limit to max_items
        evidence_texts = evidence_texts[:max_items]
        
        # Join with separators
        formatted = "\n---\n".join(evidence_texts)
        
        return formatted
    
    @staticmethod
    def has_evidence(evidence_texts: List[str]) -> bool:
        """
        Check if there is any meaningful evidence.
        
        Args:
            evidence_texts: List of evidence text strings
            
        Returns:
            True if evidence exists, False otherwise
        """
        return bool(evidence_texts and any(text.strip() for text in evidence_texts))

