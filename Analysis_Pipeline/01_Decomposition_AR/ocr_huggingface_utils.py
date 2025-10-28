"""
OCR and document parsing utilities using Hugging Face Deepseek OCR API.

This module provides functions to extract text from PDF documents
using Hugging Face's Deepseek OCR model and parse them into structured sections.
"""

import os
import re
import json
import requests
import base64
import io
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import logging

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

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


class HuggingFaceDeepseekOCRParser:
    """Parse documents using Hugging Face Deepseek OCR API."""
    
    def __init__(self, api_token: str = None):
        """
        Initialize the Hugging Face Deepseek OCR parser.
        
        Args:
            api_token: Hugging Face API token. If None, will try to load from environment.
        """
        self.api_token = api_token or os.getenv('HUGGINGFACE_API_TOKEN')
        if not self.api_token:
            raise ValueError(
                "Hugging Face API token not found. Please set HUGGINGFACE_API_TOKEN environment variable "
                "or pass api_token parameter."
            )
        
        self.text_cleaner = TextCleaner()
        self.sentence_splitter = SentenceSplitter()
        self.api_url = "https://api-inference.huggingface.co/models/deepseek-ai/DeepSeek-OCR"
        
        # Check if PyMuPDF is available
        if fitz is None:
            logger.warning("PyMuPDF not installed. PDF processing will not work.")
            logger.info("Install with: pip install PyMuPDF")
        
        logger.info("HuggingFaceDeepseekOCRParser initialized")
    
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from PDF using Hugging Face Deepseek OCR API.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ImportError: If pdf2image is not installed
            requests.RequestException: If API request fails
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if fitz is None:
            raise ImportError(
                "PyMuPDF is required for PDF processing. Install with: pip install PyMuPDF"
            )
        
        logger.info(f"Extracting text from PDF using Hugging Face Deepseek OCR: {pdf_path}")
        
        try:
            # Convert PDF to images using PyMuPDF
            logger.info("Converting PDF pages to images using PyMuPDF...")
            pdf = fitz.open(str(pdf_path))
            logger.info(f"Converted {len(pdf)} pages to images")
            
            results = []
            headers = {"Authorization": f"Bearer {self.api_token}"}
            
            for page_num in range(len(pdf)):
                logger.info(f"Processing page {page_num+1}/{len(pdf)}...")
                
                # Get page and convert to pixmap
                page = pdf[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))  # 300 DPI
                
                # Convert pixmap to bytes
                image_bytes = pix.tobytes("jpeg")
                
                # Base64 encoding
                b64_image = base64.b64encode(image_bytes).decode("utf-8")
                
                # Prepare payload for Hugging Face API
                payload = {
                    "inputs": {
                        "type": "input_image",
                        "image": b64_image
                    },
                    "parameters": {
                        "max_new_tokens": 2048,
                        "return_full_text": True
                    }
                }
                
                # Send request to Hugging Face API
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Page {page_num+1} processed successfully")
                    results.append(result)
                else:
                    error_msg = f"Hugging Face API error for page {page_num+1}: {response.status_code}"
                    try:
                        error_details = response.json()
                        error_msg += f" - {error_details}"
                    except:
                        error_msg += f" - {response.text}"
                    
                    logger.error(error_msg)
                    raise requests.RequestException(error_msg)
            
            # Combine results from all pages
            logger.info("Combining results from all pages...")
            full_text = "\n\n".join([
                r[0]["generated_text"] if isinstance(r, list) and len(r) > 0 and "generated_text" in r[0] 
                else str(r) for r in results
            ])
            
            logger.info(f"✅ OCR completed. Extracted {len(full_text)} characters from {len(pdf)} pages.")
            return full_text
            
        except requests.RequestException as e:
            logger.error(f"Hugging Face API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Hugging Face OCR extraction failed: {e}", exc_info=True)
            raise RuntimeError(f"Failed to extract text from PDF using Hugging Face Deepseek OCR: {e}")
        finally:
            # Close the PDF document
            if 'pdf' in locals():
                pdf.close()
    
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
    
    def parse_text_to_sections(self, text: str) -> Dict[str, List[str]]:
        """
        Parse plain text into sections based on common patterns.
        
        This extracts sections from text using common patterns like headers,
        bullet points, and paragraph breaks.
        
        Args:
            text: Plain text from Hugging Face Deepseek OCR
            
        Returns:
            Dictionary mapping section names to lists of sentences
        """
        logger.info("Parsing text into sections")
        
        sections = {}
        current_section = "Introduction"  # Default section name
        current_text = []
        
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Check if line looks like a header (all caps, short, or starts with numbers)
            if (line.isupper() and len(line) < 50) or re.match(r'^\d+\.?\s+[A-Z]', line):
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
                current_section = line
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
            logger.warning("No clear sections found, treating as single section")
            cleaned = self.text_cleaner.clean_text(text)
            sentences = self.sentence_splitter.split_sentences(cleaned)
            sections["Full Document"] = sentences
        
        logger.info(f"Parsed {len(sections)} sections from text")
        return sections
    
    def parse_pdf_to_sections(
        self,
        pdf_path: Path,
        save_ocr_output: bool = True,
        ocr_output_base_dir: Path = None,
        use_cached: bool = True
    ) -> Dict[str, List[str]]:
        """
        Parse PDF directly into sections with sentences.
        
        Args:
            pdf_path: Path to PDF file
            save_ocr_output: Whether to save OCR output (text and JSON)
            ocr_output_base_dir: Base directory for OCR output (default: 01_Decomposition_AR/ocr_content)
            use_cached: Whether to use cached OCR output if available (default: True)
            
        Returns:
            Dictionary mapping section names to lists of sentences
        """
        logger.info(f"Parsing PDF to sections: {pdf_path}")
        
        # Determine output directory
        if ocr_output_base_dir is None:
            # Default to 01_Decomposition_AR/ocr_content
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
            logger.info("No cached OCR output found. Processing PDF with Hugging Face Deepseek OCR...")
        else:
            logger.info("Cached output disabled. Processing PDF with Hugging Face Deepseek OCR...")
        
        # Extract text from PDF using Hugging Face Deepseek OCR
        extracted_text = self.extract_text_from_pdf(pdf_path)
        
        # Parse text into sections
        sections = self.parse_text_to_sections(extracted_text)
        
        # Save OCR output if requested
        if save_ocr_output:
            # Output directory already determined above
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save raw text
            text_path = output_dir / "extracted_text.txt"
            with open(text_path, 'w', encoding='utf-8') as f:
                f.write(extracted_text)
            logger.info(f"Saved extracted text to: {text_path}")
            
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
                "total_characters": len(extracted_text),
                "ocr_provider": "huggingface_deepseek",
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
    parser = HuggingFaceDeepseekOCRParser()
    return parser.parse_sections_from_text(text_dict)
