"""
Encoding utilities for text processing and embeddings.

This module provides utilities for text encoding, preprocessing,
and embedding operations used in the RAG pipeline.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class EncodingUtils:
    """
    Utilities for text encoding and preprocessing.
    
    This class handles:
    - Text cleaning and preprocessing
    - Sentence tokenization
    - Text normalization
    - Encoding operations
    """
    
    def __init__(self):
        """Initialize the encoding utilities."""
        logger.info("EncodingUtils initialized")
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text for processing.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation
        text = re.sub(r'[^\w\s.,!?;:()\-]', '', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Simple sentence splitting (can be enhanced with NLP libraries)
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter sentences
        sentences = [
            self.clean_text(sentence) 
            for sentence in sentences 
            if self.clean_text(sentence)
        ]
        
        return sentences
    
    def preprocess_sentence(self, sentence: str) -> str:
        """
        Preprocess a sentence for matching.
        
        Args:
            sentence: Sentence to preprocess
            
        Returns:
            Preprocessed sentence
        """
        if not sentence:
            return ""
        
        # Clean the text
        sentence = self.clean_text(sentence)
        
        # Convert to lowercase for better matching
        sentence = sentence.lower()
        
        # Remove common stop words (basic implementation)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        words = sentence.split()
        words = [word for word in words if word not in stop_words]
        
        return ' '.join(words)
    
    def extract_key_terms(self, text: str, max_terms: int = 10) -> List[str]:
        """
        Extract key terms from text for better matching.
        
        Args:
            text: Text to extract terms from
            max_terms: Maximum number of terms to extract
            
        Returns:
            List of key terms
        """
        if not text:
            return []
        
        # Simple term extraction (can be enhanced with NLP)
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
        words = [word for word in words if word not in stop_words and len(word) > 2]
        
        # Count word frequency
        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency and return top terms
        sorted_terms = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [term for term, count in sorted_terms[:max_terms]]
    
    def create_query_variants(self, sentence: str) -> List[str]:
        """
        Create query variants for better matching.
        
        Args:
            sentence: Original sentence
            
        Returns:
            List of query variants
        """
        if not sentence:
            return []
        
        variants = [sentence]
        
        # Add preprocessed version
        preprocessed = self.preprocess_sentence(sentence)
        if preprocessed != sentence.lower():
            variants.append(preprocessed)
        
        # Add key terms as a query
        key_terms = self.extract_key_terms(sentence, max_terms=5)
        if key_terms:
            variants.append(' '.join(key_terms))
        
        return variants
    
    def format_evidence_for_output(
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
    
    def validate_text_quality(self, text: str) -> Dict[str, Any]:
        """
        Validate the quality of text for processing.
        
        Args:
            text: Text to validate
            
        Returns:
            Dictionary with quality metrics
        """
        if not text:
            return {
                "is_valid": False,
                "length": 0,
                "word_count": 0,
                "sentence_count": 0,
                "issues": ["Empty text"]
            }
        
        # Basic quality checks
        issues = []
        
        # Check length
        if len(text) < 10:
            issues.append("Text too short")
        
        # Check word count
        words = text.split()
        word_count = len(words)
        if word_count < 3:
            issues.append("Too few words")
        
        # Check sentence count
        sentences = self.split_into_sentences(text)
        sentence_count = len(sentences)
        
        # Check for repetitive content
        if len(set(words)) < len(words) * 0.5:
            issues.append("High repetition in text")
        
        return {
            "is_valid": len(issues) == 0,
            "length": len(text),
            "word_count": word_count,
            "sentence_count": sentence_count,
            "issues": issues
        }
