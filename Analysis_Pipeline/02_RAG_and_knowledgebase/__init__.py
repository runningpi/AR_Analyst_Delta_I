"""
RAG and Knowledge Base module for AR Analyst Delta I pipeline.

This module handles:
- Knowledge base creation and management using DS-RAG
- Sentence matching against company documents
- Evidence retrieval and ranking
"""

from .DS_RAG_utils import KnowledgeBaseManager
from .matching_utils import SentenceMatcher

__all__ = ['KnowledgeBaseManager', 'SentenceMatcher']
