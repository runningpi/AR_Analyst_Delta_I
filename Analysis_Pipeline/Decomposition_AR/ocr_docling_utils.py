"""
OCR and document parsing utilities using Docling.

This module provides functions to extract text from PDF documents
using Docling OCR and parse them into structured sections.
"""

import os
import re
from pathlib import Path
from typing import Dict, List
import logging

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

logger = logging.getLogger(__name__)


class TextCleaner:
    """Utility class for cleaning and normalizing text."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean text by removing unwanted characters and normalizing whitespace.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        # Remove literal newlines, carriage returns, and protected spaces
        text = text.replace("\r", " ").replace("\n", " ").replace("\\n", " ").replace("\u00a0", " ")
        
        # Collapse multiple whitespace to single space
        text = re.sub(r"\s+", " ", text).strip()
        
        return text


class SentenceSplitter:
    """Split text into sentences with abbreviation handling."""
    
    # Common abbreviations that shouldn't trigger sentence splits
    ABBREVIATIONS = r'(?:vs|Inc|Co|Corp|Ltd|Mr|Ms|Mrs|Dr|Prof|Jr|Sr|St|No|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'
    
    @classmethod
    def split_sentences(cls, text: str) -> List[str]:
        """
        Split text into sentences, handling abbreviations and edge cases.
        
        Args:
            text: Text to split into sentences
            
        Returns:
            List of sentences
        """
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Protect dots in abbreviations, decimals, and initials
        text = re.sub(fr'\b{cls.ABBREVIATIONS}\.', lambda m: m.group(0)[:-1] + '<prd>', text)
        text = re.sub(r'(?<=\d)\.(?=\d)', '<prd>', text)  # Decimals like 4.5
        text = re.sub(r'(?<=[A-Z])\.(?=[A-Z]\.)', '<prd>', text)  # Initials like U.S.A.
        
        # Split on sentence boundaries
        parts = re.split(r'(?<=[.!?])\s+', text)
        sentences = [p.replace('<prd>', '.').strip() for p in parts if p.strip()]
        
        # Merge fragments (e.g., standalone "CFO.")
        merged = []
        i = 0
        while i < len(sentences):
            # If sentence is just an abbreviation and there's a next sentence, merge them
            if re.fullmatch(r'[A-Z]{2,}\.', sentences[i]) and i + 1 < len(sentences):
                merged.append(sentences[i] + ' ' + sentences[i + 1])
                i += 2
            else:
                merged.append(sentences[i])
                i += 1
        
        return merged


class DoclingParser:
    """Parse documents using Docling (placeholder for actual implementation)."""
    
    def __init__(self):
        """Initialize the Docling parser."""
        self.text_cleaner = TextCleaner()
        self.sentence_splitter = SentenceSplitter()
        logger.info("DoclingParser initialized")
    
    def extract_text_from_pdf(
        self,
        pdf_path: Path,
        force_full_page_ocr: bool = True,
        do_table_structure: bool = True,
        use_gpu: bool = False,
    ) -> str:
        """
        Extract text from PDF using Docling OCR.
        
        Args:
            pdf_path: Path to PDF file
            force_full_page_ocr: Whether to force full page OCR (useful for scanned docs)
            do_table_structure: Whether to extract table structures
            use_gpu: Whether to use GPU acceleration (default: False for compatibility)
            
        Returns:
            Extracted text in Markdown format
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Extracting text from PDF using Docling: {pdf_path}")
        
        # Force CPU usage if GPU is disabled (fixes RTX 5090 CUDA compatibility issue)
        if not use_gpu:
            logger.info("Forcing CPU usage for OCR (GPU disabled for compatibility)")
            os.environ['CUDA_VISIBLE_DEVICES'] = '-1'  # Disable CUDA
        
        try:
            # Configure pipeline options
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = do_table_structure
            
            if do_table_structure:
                pipeline_options.table_structure_options.do_cell_matching = True
            
            # Configure OCR options (using EasyOCR with CPU)
            ocr_options = EasyOcrOptions(
                force_full_page_ocr=force_full_page_ocr,
                use_gpu=use_gpu  # Force CPU usage
            )
            pipeline_options.ocr_options = ocr_options
            
            # Initialize the DocumentConverter with the specified options
            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options,
                    )
                }
            )
            
            # Convert the document
            logger.info(f"Processing document with Docling (GPU: {use_gpu})...")
            result = converter.convert(pdf_path)
            doc = result.document
            
            # Export to Markdown
            markdown_text = doc.export_to_markdown()
            
            logger.info(f"✅ OCR completed. Extracted {len(markdown_text)} characters.")
            return markdown_text
            
        except Exception as e:
            logger.error(f"Docling extraction failed: {e}", exc_info=True)
            raise RuntimeError(
                f"Failed to extract text from PDF using Docling: {e}\n"
                "Make sure Docling is installed: pip install docling\n"
                "If you see CUDA errors, the pipeline will automatically use CPU."
            )
        finally:
            # Restore CUDA visibility
            if not use_gpu and 'CUDA_VISIBLE_DEVICES' in os.environ:
                del os.environ['CUDA_VISIBLE_DEVICES']
    
    def parse_sections_from_text(self, text_dict: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Parse text dictionary into sections with sentences.
        
        Args:
            text_dict: Dictionary mapping section names to section text
            
        Returns:
            Dictionary mapping section names to lists of sentences
        """
        logger.info(f"Parsing {len(text_dict)} sections into sentences")
        
        results = {}
        for section_name, section_text in text_dict.items():
            # Clean the text
            cleaned_text = self.text_cleaner.clean_text(section_text)
            
            # Split into sentences
            sentences = self.sentence_splitter.split_sentences(cleaned_text)
            
            results[section_name] = sentences
            logger.debug(f"Section '{section_name}': {len(sentences)} sentences")
        
        logger.info(f"Parsed total of {sum(len(s) for s in results.values())} sentences")
        return results
    
    def parse_markdown_to_sections(self, markdown_text: str) -> Dict[str, List[str]]:
        """
        Parse markdown text into sections based on headers.
        
        This extracts sections from markdown using headers (# Header, ## Header, etc.)
        
        Args:
            markdown_text: Markdown text from Docling
            
        Returns:
            Dictionary mapping section names to lists of sentences
        """
        logger.info("Parsing markdown into sections")
        
        sections = {}
        current_section = "Introduction"  # Default section name
        current_text = []
        
        lines = markdown_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check if line is a header
            if line.startswith('#'):
                # Save previous section
                if current_text:
                    section_text = ' '.join(current_text)
                    cleaned = self.text_cleaner.clean_text(section_text)
                    if cleaned:
                        sentences = self.sentence_splitter.split_sentences(cleaned)
                        if sentences:
                            sections[current_section] = sentences
                            logger.debug(f"Section '{current_section}': {len(sentences)} sentences")
                
                # Start new section
                # Remove markdown header symbols and clean
                current_section = re.sub(r'^#+\s*', '', line).strip()
                if not current_section:
                    current_section = "Untitled Section"
                current_text = []
            
            elif line:  # Non-empty line
                current_text.append(line)
        
        # Save last section
        if current_text:
            section_text = ' '.join(current_text)
            cleaned = self.text_cleaner.clean_text(section_text)
            if cleaned:
                sentences = self.sentence_splitter.split_sentences(cleaned)
                if sentences:
                    sections[current_section] = sentences
                    logger.debug(f"Section '{current_section}': {len(sentences)} sentences")
        
        # If no sections were found, treat entire text as one section
        if not sections:
            logger.warning("No markdown headers found, treating as single section")
            cleaned = self.text_cleaner.clean_text(markdown_text)
            sentences = self.sentence_splitter.split_sentences(cleaned)
            sections["Full Document"] = sentences
        
        logger.info(f"Parsed {len(sections)} sections from markdown")
        return sections
    
    def parse_pdf_to_sections(
        self,
        pdf_path: Path,
        use_gpu: bool = False,
        save_ocr_output: bool = True,
        ocr_output_base_dir: Path = None,
        use_cached: bool = True
    ) -> Dict[str, List[str]]:
        """
        Parse PDF directly into sections with sentences.
        
        Args:
            pdf_path: Path to PDF file
            use_gpu: Whether to use GPU for OCR (default: False for compatibility)
            save_ocr_output: Whether to save OCR output (markdown and JSON)
            ocr_output_base_dir: Base directory for OCR output (default: Decomposition_AR/ocr_content)
            use_cached: Whether to use cached OCR output if available (default: True)
            
        Returns:
            Dictionary mapping section names to lists of sentences
        """
        import json
        from datetime import datetime
        
        logger.info(f"Parsing PDF to sections: {pdf_path}")
        
        # Determine output directory
        if ocr_output_base_dir is None:
            # Default to Decomposition_AR/ocr_content
            script_dir = Path(__file__).parent
            ocr_output_base_dir = script_dir / "ocr_content"
        
        # Create directory name based on PDF filename
        pdf_name = pdf_path.stem  # Filename without extension
        output_dir = ocr_output_base_dir / pdf_name
        sections_path = output_dir / "extracted_sections.json"
        
        # Check if cached OCR output exists
        if use_cached and sections_path.exists():
            logger.info(f"✓ Found cached OCR output at: {sections_path}")
            logger.info("Loading sections from cached file (skipping OCR processing)...")
            
            try:
                with open(sections_path, 'r', encoding='utf-8') as f:
                    sections = json.load(f)
                
                logger.info(f"✓ Loaded {len(sections)} sections from cache")
                logger.info(f"  Total sentences: {sum(len(sents) for sents in sections.values())}")
                
                # Load and display metadata if available
                metadata_path = output_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    logger.info(f"  Originally extracted: {metadata.get('extracted_at', 'unknown')}")
                
                return sections
                
            except Exception as e:
                logger.warning(f"Failed to load cached OCR output: {e}")
                logger.info("Falling back to fresh OCR extraction...")
        
        # No cached output or use_cached=False: proceed with fresh extraction
        if use_cached:
            logger.info("No cached OCR output found. Processing PDF with Docling...")
        else:
            logger.info("Cached output disabled. Processing PDF with Docling...")
        
        # Extract text from PDF using Docling (with CPU by default)
        markdown_text = self.extract_text_from_pdf(pdf_path, use_gpu=use_gpu)
        
        # Parse markdown into sections
        sections = self.parse_markdown_to_sections(markdown_text)
        
        # Save OCR output if requested
        if save_ocr_output:
            # Output directory already determined above
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save markdown
            markdown_path = output_dir / "extracted_text.md"
            with open(markdown_path, 'w', encoding='utf-8') as f:
                f.write(markdown_text)
            logger.info(f"Saved markdown to: {markdown_path}")
            
            # Save structured sections as JSON
            sections_path = output_dir / "extracted_sections.json"
            with open(sections_path, 'w', encoding='utf-8') as f:
                json.dump(sections, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved sections JSON to: {sections_path}")
            
            # Save metadata
            metadata = {
                "pdf_file": str(pdf_path),
                "pdf_filename": pdf_path.name,
                "extracted_at": datetime.now().isoformat(),
                "total_sections": len(sections),
                "total_sentences": sum(len(sents) for sents in sections.values()),
                "total_characters": len(markdown_text),
                "use_gpu": use_gpu,
                "sections_list": list(sections.keys())
            }
            metadata_path = output_dir / "metadata.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved metadata to: {metadata_path}")
            
            logger.info(f"OCR output saved to directory: {output_dir}")
        
        logger.info(f"Successfully parsed PDF into {len(sections)} sections")
        return sections


def extract_sentences_per_section(text_dict: Dict[str, str]) -> Dict[str, List[str]]:
    """
    Convenience function to extract sentences from section dictionary.
    
    Args:
        text_dict: Dictionary mapping section names to section text
        
    Returns:
        Dictionary mapping section names to lists of sentences
    """
    parser = DoclingParser()
    return parser.parse_sections_from_text(text_dict)

