"""
DS-RAG utilities for knowledge base management.

This module provides the KnowledgeBaseManager class that serves as an interface
between the pipeline and the DS-RAG framework for:
- Creating and initializing knowledge bases
- Adding company documents to the knowledge base
- Querying the knowledge base for relevant evidence
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

try:
    from dsrag.knowledge_base import KnowledgeBase
except ImportError:
    raise ImportError(
        "dsrag library not found. Please install it with: pip install dsrag"
    )

logger = logging.getLogger(__name__)


class KnowledgeBaseManager:
    """
    Manager for DS-RAG knowledge base operations.
    
    This class wraps the DS-RAG KnowledgeBase and provides a simplified
    interface for initializing, populating, and querying knowledge bases.
    """
    
    def __init__(
        self,
        kb_id: str,
        storage_directory: Union[str, Path],
        llm_model: str = "gpt-4o-mini",
        use_reranker: bool = True,
        use_semantic_sectioning: bool = True,
        chunk_size: Optional[int] = None,
        exists_ok: bool = True,
    ):
        """
        Initialize the knowledge base manager.
        
        Args:
            kb_id: Unique identifier for the knowledge base
            storage_directory: Directory where KB data will be stored
            llm_model: Model name for embeddings (default: "gpt-4o-mini")
            use_reranker: Whether to use Cohere reranking (default: True)
            use_semantic_sectioning: Whether to use semantic sectioning (default: True)
            chunk_size: Optional chunk size override
            exists_ok: If True, load existing KB if it exists (default: True)
        
        Raises:
            ValueError: If required API keys are missing
            RuntimeError: If knowledge base initialization fails
        """
        self.kb_id = kb_id
        self.storage_directory = Path(storage_directory)
        self.llm_model = llm_model
        self.use_reranker = use_reranker
        self.use_semantic_sectioning = use_semantic_sectioning
        self.chunk_size = chunk_size
        self.exists_ok = exists_ok
        
        # Check for required API keys
        self._check_api_keys()
        
        # Create storage directory if it doesn't exist
        self.storage_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize knowledge base
        try:
            logger.info(f"Initializing knowledge base: {kb_id}")
            logger.info(f"Storage directory: {self.storage_directory}")
            
            # DS-RAG KnowledgeBase initialization
            # Note: DS-RAG handles reranking and semantic sectioning internally
            # based on API key availability
            self.kb = KnowledgeBase(
                kb_id=kb_id,
                storage_directory=str(self.storage_directory),
                exists_ok=exists_ok,
            )
            
            logger.info(f"Knowledge base '{kb_id}' initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            raise RuntimeError(f"Knowledge base initialization failed: {e}")
    
    def _check_api_keys(self) -> None:
        """
        Check for required API keys and raise errors if missing.
        
        Raises:
            ValueError: If OPENAI_API_KEY is missing
            ValueError: If CO_API_KEY is missing when use_reranker=True
        """
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please set it in your .env file or environment."
            )
        
        if self.use_reranker and not os.getenv("CO_API_KEY"):
            logger.warning(
                "CO_API_KEY not found but use_reranker=True. "
                "Reranking will be disabled."
            )
            # Note: DS-RAG will automatically disable reranking if key is missing
    
    def add_document(
        self,
        doc_id: str,
        text: Optional[str] = None,
        file_path: Optional[Union[str, Path]] = None,
    ) -> str:
        """
        Add a single document to the knowledge base.
        
        Args:
            doc_id: Unique identifier for the document
            text: Optional text content to add (if provided, this takes precedence)
            file_path: Optional path to a file to add (PDF, TXT, MD, etc.)
        
        Returns:
            Document ID that was added
        
        Raises:
            ValueError: If neither text nor file_path is provided
            FileNotFoundError: If file_path is provided but file doesn't exist
        """
        if text is not None:
            # Add document from text
            logger.info(f"Adding document '{doc_id}' from text (length: {len(text)} chars)")
            try:
                # DS-RAG's add_document requires file_path
                # Write text to a temporary file in the storage directory
                # This ensures the file persists long enough for DS-RAG to process it
                temp_dir = self.storage_directory / "temp_documents"
                temp_dir.mkdir(exist_ok=True)
                
                # Create temp file with doc_id in name for easier debugging
                temp_file = temp_dir / f"{doc_id}_temp.txt"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(text)
                
                self.kb.add_document(doc_id=doc_id, file_path=str(temp_file))
                
                # Clean up temp file after processing
                # DS-RAG processes files synchronously, so it's safe to delete immediately
                try:
                    temp_file.unlink()
                except:
                    logger.debug(f"Could not delete temp file {temp_file}, will be cleaned up later")
                    
                logger.debug(f"Document '{doc_id}' added successfully from text")
                
            except Exception as e:
                logger.error(f"Failed to add document '{doc_id}' from text: {e}")
                raise
                
        elif file_path is not None:
            # Add document from file
            file_path = Path(file_path)
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            logger.info(f"Adding document '{doc_id}' from file: {file_path}")
            try:
                self.kb.add_document(doc_id=doc_id, file_path=str(file_path))
                logger.debug(f"Document '{doc_id}' added successfully from file")
                
            except Exception as e:
                logger.error(f"Failed to add document '{doc_id}' from file: {e}")
                raise
        else:
            raise ValueError("Either 'text' or 'file_path' must be provided")
        
        return doc_id
    
    def add_documents_from_directory(
        self,
        directory: Union[str, Path],
        file_pattern: str = "*",
    ) -> List[str]:
        """
        Add multiple documents from a directory to the knowledge base.
        
        This method scans the directory for files matching the pattern,
        then calls add_document() for each file.
        
        Args:
            directory: Directory path to scan for documents
            file_pattern: Glob pattern to match files (e.g., "*.pdf", "*.txt", "*.md")
        
        Returns:
            List of document IDs that were added
        
        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Path is not a directory: {directory}")
        
        logger.info(f"Scanning directory '{directory}' for files matching '{file_pattern}'")
        
        # Find all matching files
        matching_files = list(directory.glob(file_pattern))
        
        if not matching_files:
            logger.warning(f"No files found matching pattern '{file_pattern}' in {directory}")
            return []
        
        logger.info(f"Found {len(matching_files)} files to add to knowledge base")
        
        doc_ids = []
        for file_path in matching_files:
            try:
                # Use stem (filename without extension) as doc_id
                doc_id = file_path.stem
                
                # Check if document already exists (DS-RAG handles this, but we log it)
                self.add_document(doc_id=doc_id, file_path=file_path)
                doc_ids.append(doc_id)
                
                logger.debug(f"Added document: {file_path.name} (doc_id: {doc_id})")
                
            except Exception as e:
                logger.error(f"Failed to add document from {file_path}: {e}")
                # Continue with other files instead of failing completely
                continue
        
        logger.info(f"Successfully added {len(doc_ids)} documents to knowledge base")
        return doc_ids
    
    def query(
        self,
        query_text: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Query the knowledge base for relevant evidence.
        
        Args:
            query_text: The query text to search for
            top_k: Maximum number of results to return (default: 5)
        
        Returns:
            List of result dictionaries, each containing:
            - content: The text content of the matching chunk
            - score: Relevance score (if available)
            - doc_id: Document identifier
            - chunk_start: Position in document (if available)
            - chunk_end: Position in document (if available)
            - metadata: Additional metadata (if available)
        
        Returns empty list if no results found or on error.
        """
        if not query_text or not query_text.strip():
            logger.warning("Empty query text provided")
            return []
        
        try:
            logger.debug(f"Querying knowledge base with: '{query_text[:100]}...' (top_k={top_k})")
            
            # DS-RAG query expects a list of queries
            # Results are returned as a nested list structure
            results = self.kb.query([query_text])
            
            # DS-RAG returns results as: [[result1, result2, ...]]
            # We need to extract the first (and only) query's results
            if not results:
                logger.debug("No results returned from knowledge base")
                return []
            
            # Flatten results if needed
            query_results = results[0] if isinstance(results, list) and results else results
            if not isinstance(query_results, list):
                query_results = [query_results]
            
            # Limit to top_k
            query_results = query_results[:top_k]
            
            # Format results into the expected dictionary structure
            formatted_results = []
            for i, result in enumerate(query_results):
                # DS-RAG results can be dicts or objects
                # Extract common fields
                if isinstance(result, dict):
                    content = result.get("text", result.get("content", ""))
                    score = result.get("score", result.get("relevance_score", 0.0))
                    metadata = result.get("metadata", {})
                else:
                    # Try to access as attributes
                    content = getattr(result, "text", getattr(result, "content", ""))
                    score = getattr(result, "score", getattr(result, "relevance_score", 0.0))
                    metadata = getattr(result, "metadata", {})
                
                # Extract doc_id from metadata or result
                if isinstance(result, dict):
                    doc_id = result.get("doc_id") or metadata.get("doc_id") or metadata.get("document_id", "")
                else:
                    doc_id = getattr(result, "doc_id", None) or metadata.get("doc_id", "") or metadata.get("document_id", "")
                
                # Extract chunk position if available
                chunk_start = metadata.get("chunk_start", metadata.get("start", 0))
                chunk_end = metadata.get("chunk_end", metadata.get("end", 0))
                
                formatted_result = {
                    "content": str(content) if content else "",
                    "score": float(score) if score is not None else 0.0,
                    "doc_id": str(doc_id) if doc_id else "",
                    "chunk_start": int(chunk_start) if chunk_start is not None else 0,
                    "chunk_end": int(chunk_end) if chunk_end is not None else 0,
                    "metadata": metadata if isinstance(metadata, dict) else {},
                }
                
                formatted_results.append(formatted_result)
            
            logger.debug(f"Query returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}", exc_info=True)
            return []

