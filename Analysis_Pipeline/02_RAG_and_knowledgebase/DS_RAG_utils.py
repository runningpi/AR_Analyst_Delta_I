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
        
        # Preprocess file to handle encoding issues
        processed_file_path = self._preprocess_file_for_encoding(file_path)
        
        try:
            self.kb.add_document(
                doc_id=doc_id,
                file_path=str(processed_file_path),
                chunk_size=chunk_size,
                semantic_sectioning_config={
                    "use_semantic_sectioning": self.use_semantic_sectioning
                }
            )
            logger.info(f"Successfully added document: {doc_id}")
            
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}", exc_info=True)
            raise
        finally:
            # Clean up temporary file if it was created
            if processed_file_path != file_path and processed_file_path.exists():
                try:
                    processed_file_path.unlink()
                    logger.debug(f"Cleaned up temporary file: {processed_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {processed_file_path}: {e}")
    
    def _preprocess_file_for_encoding(self, file_path: Path) -> Path:
        """
        Preprocess a file to handle encoding issues before passing to DS-RAG.
        
        Args:
            file_path: Path to the original file
            
        Returns:
            Path to the processed file (may be the same as input if no issues found)
        """
        try:
            # First, try to read the file with UTF-8 encoding
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"File {file_path} is readable with UTF-8 encoding")
            return file_path  # No preprocessing needed
            
        except UnicodeDecodeError as e:
            logger.warning(f"File {file_path} has encoding issues: {e}")
            return self._create_utf8_version(file_path)
    
    def _create_utf8_version(self, file_path: Path) -> Path:
        """
        Create a UTF-8 version of a file with encoding issues.
        
        Args:
            file_path: Path to the original file
            
        Returns:
            Path to the UTF-8 version
        """
        import tempfile
        
        # Create a temporary file with UTF-8 encoding
        temp_dir = self.storage_directory / "temp_encoding_fixes"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / f"utf8_{file_path.name}"
        
        try:
            logger.info(f"Creating UTF-8 version of {file_path.name}")
            
            # Try multiple encodings to read the file
            content = None
            used_encoding = None
            
            for encoding in ['cp1252', 'latin-1', 'iso-8859-1', 'utf-8']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                        content = f.read()
                    used_encoding = encoding
                    logger.info(f"Successfully read {file_path.name} with {encoding} encoding")
                    break
                except Exception as e:
                    logger.debug(f"Failed to read with {encoding}: {e}")
                    continue
            
            if content is None:
                raise ValueError(f"Could not read {file_path.name} with any encoding")
            
            # Clean problematic characters
            content = self._clean_problematic_characters(content)
            
            # Write as UTF-8 with BOM to ensure compatibility
            with open(temp_file, 'w', encoding='utf-8-sig', errors='replace') as f:
                f.write(content)
            
            # Verify the file can be read back
            try:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    test_content = f.read()
                logger.info(f"Successfully created UTF-8 version: {temp_file.name}")
                return temp_file
            except Exception as e:
                logger.error(f"Failed to verify UTF-8 file {temp_file.name}: {e}")
                if temp_file.exists():
                    temp_file.unlink()
                raise
                
        except Exception as e:
            logger.error(f"Error creating UTF-8 version of {file_path}: {e}")
            if temp_file.exists():
                temp_file.unlink()
            raise
    
    def _fix_file_encoding(self, file_path: Path) -> None:
        """Fix encoding issues in a file by cleaning problematic characters."""
        try:
            logger.info(f"Attempting to fix encoding issues in {file_path}")
            
            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + '.backup')
            
            # Read file with multiple encoding attempts
            content = None
            for encoding in ['utf-8', 'cp1252', 'latin-1', 'iso-8859-1']:
                try:
                    with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                        content = f.read()
                    logger.info(f"Successfully read {file_path.name} with {encoding} encoding")
                    break
                except Exception:
                    continue
            
            if content is None:
                logger.error(f"Could not read {file_path.name} with any encoding")
                return
            
            # Create backup
            with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
                dst.write(src.read())
            
            # Clean problematic characters
            content = self._clean_problematic_characters(content)
            
            # Write back as UTF-8 with BOM
            with open(file_path, 'w', encoding='utf-8-sig', errors='replace') as f:
                f.write(content)
            
            # Test that the file can be read back
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    test_content = f.read()
                logger.info(f"Successfully fixed encoding for {file_path.name}")
                # Remove backup if successful
                backup_path.unlink()
            except Exception as e:
                logger.error(f"Failed to verify fixed file {file_path.name}: {e}")
                # Restore backup
                with open(backup_path, 'rb') as src, open(file_path, 'wb') as dst:
                    dst.write(src.read())
                backup_path.unlink()
                
        except Exception as e:
            logger.error(f"Error fixing encoding for {file_path}: {e}")
    
    def _clean_problematic_characters(self, content: str) -> str:
        """Clean problematic characters from content."""
        if not content:
            return ""
        
        # Replace problematic Unicode characters
        replacements = {
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
            '\u00a0': ' ',  # Non-breaking space
            '\u00ad': '',   # Soft hyphen
            '\u00ae': '(R)', # Registered trademark symbol
            '\u00a9': '(C)', # Copyright symbol
            '\u2122': '(TM)', # Trademark symbol
            '\u0090': '',   # Control character (0x90 - the problematic byte)
            '\u009d': '',   # Control character
            '\u0091': '',   # Private use
            '\u0092': "'",  # Private use
            '\u0093': '"',  # Private use
            '\u0094': '"',  # Private use
            '\u0095': '*',  # Private use
            '\u0096': '-',  # Private use
            '\u0097': '-',  # Private use
            '\u0098': '',   # Private use
            '\u0099': '',   # Private use
            '\u009a': '',   # Private use
            '\u009b': '',   # Private use
            '\u009c': '',   # Private use
            '\u009e': '',   # Private use
            '\u009f': '',   # Private use
        }
        
        # Apply replacements
        for old, new in replacements.items():
            content = content.replace(old, new)
        
        # Remove any remaining control characters and non-printable characters
        # This is more aggressive cleaning to handle encoding issues
        cleaned_chars = []
        for char in content:
            char_code = ord(char)
            # Keep printable ASCII characters, newlines, tabs, and carriage returns
            if (32 <= char_code <= 126) or char in '\n\t\r':
                cleaned_chars.append(char)
            # Replace other characters with space
            else:
                cleaned_chars.append(' ')
        
        content = ''.join(cleaned_chars)
        
        # Normalize whitespace
        import re
        content = re.sub(r'\s+', ' ', content.strip())
        
        return content
    
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
    
    def add_all_documents_from_directory(
        self,
        directory: Path,
        file_patterns: List[str] = ["*.pdf", "*.txt"],
    ) -> List[str]:
        """
        Add all documents matching any of the patterns from a directory and its subdirectories.
        
        Args:
            directory: Directory containing documents
            file_patterns: List of glob patterns for files (will search recursively)
            
        Returns:
            List of document IDs that were added
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        all_files = []
        for pattern in file_patterns:
            # Use recursive glob pattern to search in subdirectories
            recursive_pattern = f"**/{pattern}"
            files = list(directory.glob(recursive_pattern))
            all_files.extend(files)
            logger.info(f"Found {len(files)} files matching {recursive_pattern} in {directory} (including subdirectories)")
        
        # Remove duplicates while preserving order
        unique_files = list(dict.fromkeys(all_files))
        logger.info(f"Total unique files to add: {len(unique_files)}")
        
        added_docs = []
        for file_path in unique_files:
            # Create a more descriptive doc_id that includes the subdirectory path
            # This helps distinguish between files with the same name in different folders
            relative_path = file_path.relative_to(directory)
            doc_id = str(relative_path).replace("/", "_").replace("\\", "_")
            
            try:
                self.add_document(doc_id, file_path)
                added_docs.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to add {file_path}: {e}")
        
        logger.info(f"Successfully added {len(added_docs)} documents to KB")
        return added_docs
    
    def add_10k_10q_documents_from_directory(
        self,
        directory: Path,
        file_patterns: List[str] = ["*.pdf", "*.txt"],
    ) -> List[str]:
        """
        Add only 10-K and 10-Q documents from a directory and its subdirectories.
        
        Args:
            directory: Directory containing documents
            file_patterns: List of glob patterns for files (will search recursively)
            
        Returns:
            List of document IDs that were added
        """
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        all_files = []
        for pattern in file_patterns:
            # Use recursive glob pattern to search in subdirectories
            recursive_pattern = f"**/{pattern}"
            files = list(directory.glob(recursive_pattern))
            all_files.extend(files)
            logger.info(f"Found {len(files)} files matching {recursive_pattern} in {directory} (including subdirectories)")
        
        # Remove duplicates while preserving order
        unique_files = list(dict.fromkeys(all_files))
        logger.info(f"Total unique files found: {len(unique_files)}")
        
        # Filter to only include documents from 10-K and 10-Q folders
        filtered_files = []
        for file_path in unique_files:
            # Check if the file is in a 10-K or 10-Q folder
            path_parts = file_path.parts
            if '10-K' in path_parts or '10-Q' in path_parts:
                filtered_files.append(file_path)
                logger.debug(f"Including document from 10-K/10-Q folder: {file_path}")
            else:
                logger.debug(f"Excluding document not in 10-K/10-Q folder: {file_path}")
        
        logger.info(f"Filtered to {len(filtered_files)} 10-K/10-Q documents out of {len(unique_files)} total files")
        
        added_docs = []
        for file_path in filtered_files:
            # Create a more descriptive doc_id that includes the subdirectory path
            # This helps distinguish between files with the same name in different folders
            relative_path = file_path.relative_to(directory)
            doc_id = str(relative_path).replace("/", "_").replace("\\", "_")
            
            try:
                self.add_document(doc_id, file_path)
                added_docs.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to add {file_path}: {e}")
        
        logger.info(f"Successfully added {len(added_docs)} 10-K/10-Q documents to KB")
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

