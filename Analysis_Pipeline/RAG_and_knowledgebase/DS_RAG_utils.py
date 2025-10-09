"""
DS-RAG Knowledge Base utilities.

This module provides a wrapper around the dsrag library for creating
and querying knowledge bases from company documents.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

from dsrag.llm import OpenAIChatAPI
from dsrag.reranker import CohereReranker
from dsrag.knowledge_base import KnowledgeBase as DSRAGKnowledgeBase

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """Manage DS-RAG knowledge base creation and querying."""
    
    def __init__(
        self,
        kb_id: str,
        storage_directory: Path,
        llm_model: str = "gpt-4o-mini",
        use_reranker: bool = True,
        chunk_size: int = 200,
        use_semantic_sectioning: bool = False,
    ):
        """
        Initialize the Knowledge Base Manager.
        
        Args:
            kb_id: Unique identifier for the knowledge base
            storage_directory: Directory to store KB data
            llm_model: OpenAI model to use for auto-context
            use_reranker: Whether to use Cohere reranker
            chunk_size: Size of text chunks
            use_semantic_sectioning: Whether to use semantic sectioning
        """
        self.kb_id = kb_id
        self.storage_directory = Path(storage_directory)
        self.chunk_size = chunk_size
        self.use_semantic_sectioning = use_semantic_sectioning
        
        # Create storage directory
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM
        self.llm = OpenAIChatAPI(model=llm_model)
        
        # Initialize reranker if requested
        self.reranker = None
        if use_reranker:
            try:
                self.reranker = CohereReranker()
                logger.info("Cohere reranker initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Cohere reranker: {e}")
        
        # Initialize knowledge base
        self.kb = DSRAGKnowledgeBase(
            kb_id=kb_id,
            reranker=self.reranker,
            auto_context_model=self.llm,
            storage_directory=str(self.storage_directory),
        )
        
        logger.info(
            f"KnowledgeBaseManager initialized: kb_id={kb_id}, "
            f"storage={self.storage_directory}"
        )
    
    def add_document(
        self,
        doc_id: str,
        file_path: Path,
        chunk_size: Optional[int] = None,
    ) -> None:
        """
        Add a document to the knowledge base.
        
        Args:
            doc_id: Unique identifier for the document
            file_path: Path to the document file
            chunk_size: Override default chunk size (optional)
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        chunk_size = chunk_size or self.chunk_size
        
        logger.info(f"Adding document to KB: {doc_id} from {file_path}")
        
        try:
            self.kb.add_document(
                doc_id=doc_id,
                file_path=str(file_path),
                chunk_size=chunk_size,
                semantic_sectioning_config={
                    "use_semantic_sectioning": self.use_semantic_sectioning
                }
            )
            logger.info(f"Successfully added document: {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}", exc_info=True)
            raise
    
    def add_documents_from_directory(
        self,
        directory: Path,
        file_pattern: str = "*.pdf",
    ) -> List[str]:
        """
        Add all documents matching pattern from a directory.
        
        Args:
            directory: Directory containing documents
            file_pattern: Glob pattern for files (default: *.pdf)
            
        Returns:
            List of document IDs that were added
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        files = list(directory.glob(file_pattern))
        logger.info(f"Found {len(files)} files matching {file_pattern} in {directory}")
        
        added_docs = []
        for file_path in files:
            doc_id = file_path.name
            try:
                self.add_document(doc_id, file_path)
                added_docs.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to add {file_path}: {e}")
        
        logger.info(f"Successfully added {len(added_docs)} documents to KB")
        return added_docs
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
    ) -> List[Any]:
        """
        Query the knowledge base.
        
        Args:
            query_text: Query text
            top_k: Number of results to return (note: DS-RAG uses internal defaults)
            
        Returns:
            List of segment results
        """
        try:
            # DS-RAG KnowledgeBase.query() doesn't accept top_k parameter
            # It uses internally configured defaults
            results = self.kb.query([query_text])
            return results
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return []
    
    def query_batch(
        self,
        queries: List[str],
        top_k: int = 5,
    ) -> Dict[str, List[Any]]:
        """
        Query the knowledge base with multiple queries.
        
        Args:
            queries: List of query texts
            top_k: Number of results per query
            
        Returns:
            Dictionary mapping query to results
        """
        results = {}
        
        for query in queries:
            results[query] = self.query(query, top_k=top_k)
        
        return results


def segment_to_text(segment: Any) -> str:
    """
    Extract text content from a segment result.
    
    Args:
        segment: Segment object from DS-RAG
        
    Returns:
        Text content as string
    """
    # Handle if segment is already a string
    if isinstance(segment, str):
        return segment
    
    # Try common attribute names
    for attr in ("content", "text", "body"):
        if hasattr(segment, attr):
            text = getattr(segment, attr)
            if isinstance(text, str):
                return text
    
    # Fallback: convert to string
    return str(segment)


def segments_to_texts(segments: List[Any]) -> List[str]:
    """
    Convert list of segments to list of text strings.
    
    Args:
        segments: List of segment objects
        
    Returns:
        List of text strings
    """
    return [segment_to_text(seg) for seg in segments]

