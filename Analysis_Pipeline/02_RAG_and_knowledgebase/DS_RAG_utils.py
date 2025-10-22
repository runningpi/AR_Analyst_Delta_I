"""
DS-RAG utilities for knowledge base management.

This module provides functionality to create and manage knowledge bases
using the DS-RAG framework for advanced RAG capabilities.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dsrag.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Manages knowledge base creation and operations using DS-RAG.
    
    This class handles:
    - Knowledge base initialization
    - Document ingestion from company reports
    - Query operations for evidence retrieval
    """
    
    def __init__(
        self,
        kb_id: str,
        storage_directory: str,
        llm_model: str = "gpt-4o-mini",
        use_reranker: bool = True,
        chunk_size: int = 1000,
        use_semantic_sectioning: bool = True
    ):
        """
        Initialize the knowledge base manager.
        
        Args:
            kb_id: Unique identifier for the knowledge base
            storage_directory: Directory to store KB data
            llm_model: LLM model for embeddings and context generation
            use_reranker: Whether to use Cohere reranking
            chunk_size: Size of text chunks for processing
            use_semantic_sectioning: Whether to use semantic sectioning
        """
        self.kb_id = kb_id
        self.storage_directory = Path(storage_directory)
        self.llm_model = llm_model
        self.use_reranker = use_reranker
        self.chunk_size = chunk_size
        self.use_semantic_sectioning = use_semantic_sectioning
        
        # Create storage directory if it doesn't exist
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize knowledge base
        self.kb = None
        self._initialize_knowledge_base()
        
        logger.info(f"KnowledgeBaseManager initialized with ID: {kb_id}")
        logger.info(f"Storage directory: {self.storage_directory}")
    
    def _initialize_knowledge_base(self) -> None:
        """Initialize the DS-RAG knowledge base."""
        try:
            # Set up API keys if not already set
            if not os.getenv("OPENAI_API_KEY"):
                logger.warning("OPENAI_API_KEY not found in environment")
            
            if self.use_reranker and not os.getenv("CO_API_KEY"):
                logger.warning("CO_API_KEY not found - reranking will be disabled")
                self.use_reranker = False
            
            # Create knowledge base
            self.kb = KnowledgeBase(
                self.kb_id,
                storage_directory=str(self.storage_directory),
                exists_ok=True
            )
            
            logger.info("Knowledge base initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            raise
    
    def add_documents_from_directory(
        self,
        directory: Path,
        file_pattern: str = "*.txt"
    ) -> List[str]:
        """
        Add all documents from a directory to the knowledge base.
        
        Args:
            directory: Directory containing documents
            file_pattern: File pattern to match (e.g., "*.txt", "*.pdf")
            
        Returns:
            List of document IDs that were added
        """
        logger.info(f"Adding documents from directory: {directory}")
        logger.info(f"File pattern: {file_pattern}")
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        added_docs = []
        
        # Find all matching files
        files = list(directory.glob(file_pattern))
        logger.info(f"Found {len(files)} files matching pattern")
        
        for file_path in files:
            try:
                # Read file content
                if file_path.suffix.lower() == '.txt':
                    text = file_path.read_text(encoding='utf-8', errors='replace')
                else:
                    logger.warning(f"Unsupported file type: {file_path.suffix}")
                    continue
                
                # Add document to knowledge base
                doc_id = file_path.name
                self.kb.add_document(doc_id=doc_id, text=text)
                added_docs.append(doc_id)
                
                logger.info(f"Added document: {doc_id}")
                
            except Exception as e:
                logger.error(f"Failed to add document {file_path.name}: {e}")
                continue
        
        logger.info(f"Successfully added {len(added_docs)} documents to knowledge base")
        return added_docs
    
    def add_document(self, doc_id: str, text: str) -> None:
        """
        Add a single document to the knowledge base.
        
        Args:
            doc_id: Unique identifier for the document
            text: Document text content
        """
        try:
            self.kb.add_document(doc_id=doc_id, text=text)
            logger.info(f"Added document: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            raise
    
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query the knowledge base for relevant documents.
        
        Args:
            query_text: Query text to search for
            top_k: Number of top results to return
            
        Returns:
            List of query results with evidence
        """
        try:
            results = self.kb.query([query_text])
            
            if not results:
                logger.warning(f"No results found for query: {query_text[:100]}...")
                return []
            
            # Return top_k results
            top_results = results[:top_k]
            
            logger.debug(f"Found {len(top_results)} results for query")
            return top_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def get_knowledge_base_info(self) -> Dict[str, Any]:
        """
        Get information about the knowledge base.
        
        Returns:
            Dictionary with KB information
        """
        return {
            "kb_id": self.kb_id,
            "storage_directory": str(self.storage_directory),
            "llm_model": self.llm_model,
            "use_reranker": self.use_reranker,
            "chunk_size": self.chunk_size,
            "use_semantic_sectioning": self.use_semantic_sectioning
        }
    
    def clear_knowledge_base(self) -> None:
        """Clear all documents from the knowledge base."""
        try:
            # Remove storage directory
            import shutil
            if self.storage_directory.exists():
                shutil.rmtree(self.storage_directory)
                logger.info("Knowledge base storage cleared")
            
            # Reinitialize
            self._initialize_knowledge_base()
            
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {e}")
            raise
