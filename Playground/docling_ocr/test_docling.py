"""
test_docling.py – OCR a local PDF with Docling, chunk the text, and show a preview

Installation:
$ pip install docling
$ pip install tesseract  # or another OCR backend

Optional OCR backends:
- Tesseract: pip install tesseract
- EasyOCR: pip install easyocr
- RapidOCR: pip install rapidocr-onnxruntime

Usage:
$ python test_docling.py
"""

from __future__ import annotations

import json
import os
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    EasyOcrOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption


# ---------------------------------------------------------------------------
#  Core OCR Functions
# ---------------------------------------------------------------------------

def ocr_pdf_with_docling(
    pdf_path: str,
    *,
    force_full_page_ocr: bool = True,
    do_table_structure: bool = True,
) -> str:
    """
    OCR a PDF using Docling and return the extracted text as Markdown.
    
    Args:
        pdf_path: Path to the PDF file
        force_full_page_ocr: Whether to force full page OCR (useful for scanned docs)
        do_table_structure: Whether to extract table structures
    
    Returns:
        Extracted text in Markdown format
    """
    print(f"Starting Docling OCR for: {os.path.basename(pdf_path)}")
    
    # Configure pipeline options
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = do_table_structure
    
    if do_table_structure:
        pipeline_options.table_structure_options.do_cell_matching = True
    
    # Configure OCR options (using EasyOCR)
    ocr_options = EasyOcrOptions(force_full_page_ocr=force_full_page_ocr)
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
    print(f"Processing document with Docling...")
    result = converter.convert(Path(pdf_path))
    doc = result.document
    
    # Export to Markdown
    markdown_text = doc.export_to_markdown()
    
    print(f"✅ OCR completed. Extracted {len(markdown_text)} characters.")
    return markdown_text


def estimate_page_from_position(
    word_index: int,
    total_words: int,
    total_pages: int
) -> int:
    """
    Estimate page number based on word position.
    Since Docling's markdown doesn't preserve page info per-word,
    we estimate based on position.
    """
    if total_words == 0:
        return 1
    ratio = word_index / total_words
    estimated_page = max(1, min(total_pages, int(ratio * total_pages) + 1))
    return estimated_page


def chunk_markdown_text(
    markdown_text: str,
    *,
    chunk_size_words: int = 300,
    estimated_total_pages: int = 1,
) -> List[Dict]:
    """
    Break markdown text into chunks of approximately chunk_size_words.
    
    Args:
        markdown_text: The markdown text to chunk
        chunk_size_words: Target number of words per chunk
        estimated_total_pages: Estimated total pages for page number estimation
    
    Returns:
        List of chunk dictionaries with metadata
    """
    print(f"Chunking text into ~{chunk_size_words} word segments...")
    
    words = markdown_text.split()
    total_words = len(words)
    chunks: List[Dict] = []
    chunk_id = 1
    
    for start in range(0, len(words), chunk_size_words):
        block = words[start : start + chunk_size_words]
        if not block:
            continue
        
        # Estimate page number based on position
        estimated_page = estimate_page_from_position(
            start, total_words, estimated_total_pages
        )
        
        # Create title from first words (max 100 chars)
        title_text = block[0] if len(block[0]) <= 100 else block[0][:100] + "..."
        
        chunks.append({
            "chunk_id": chunk_id,
            "title": title_text,
            "page_number": estimated_page,  # Estimated
            "content": " ".join(block),
            "word_count": len(block),
            "start_word_index": start,
            "end_word_index": min(start + chunk_size_words - 1, len(words) - 1)
        })
        chunk_id += 1
    
    print(f"✅ Created {len(chunks)} chunks")
    return chunks


# ---------------------------------------------------------------------------
#  High-level: PDF → chunked document data
# ---------------------------------------------------------------------------

def convert_pdf_to_chunks(
    pdf_path: str,
    *,
    chunk_size_words: int = 300,
    force_full_page_ocr: bool = True,
    do_table_structure: bool = True,
) -> Dict:
    """
    OCR a PDF with Docling and break the text into chunks.
    Returns a complete document structure with metadata and chunks.
    
    Args:
        pdf_path: Path to the PDF file
        chunk_size_words: Target words per chunk
        force_full_page_ocr: Whether to force full page OCR
        do_table_structure: Whether to extract table structures
    
    Returns:
        Dictionary containing document_info and chunks
    """
    # Step 1: OCR the PDF
    markdown_text = ocr_pdf_with_docling(
        pdf_path,
        force_full_page_ocr=force_full_page_ocr,
        do_table_structure=do_table_structure,
    )
    
    # Step 2: Estimate pages (Docling doesn't preserve page count in markdown)
    # You can extract this from the document object if needed
    estimated_pages = max(1, len(markdown_text) // 3000)  # Rough estimate
    
    # Step 3: Chunk the text
    chunks = chunk_markdown_text(
        markdown_text,
        chunk_size_words=chunk_size_words,
        estimated_total_pages=estimated_pages,
    )
    
    # Step 4: Create complete document structure
    document_data = {
        "document_info": {
            "filename": os.path.basename(pdf_path),
            "filepath": pdf_path,
            "processed_at": datetime.now().isoformat(),
            "total_pages": estimated_pages,
            "total_chunks": len(chunks),
            "chunk_size_words": chunk_size_words,
            "processing_engine": "docling",
            "ocr_backend": "easyocr",
            "force_full_page_ocr": force_full_page_ocr,
            "table_extraction_enabled": do_table_structure,
            "total_characters": len(markdown_text),
        },
        "chunks": chunks,
        "full_markdown": markdown_text,  # Include full text for reference
    }
    
    return document_data


# ---------------------------------------------------------------------------
#  Demo / CLI entry-point
# ---------------------------------------------------------------------------

def main():
    """Main function to demonstrate Docling OCR processing."""
    # PDF is in the mistral_OCR directory (sibling directory)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdf_path = os.path.join(
        base_dir,
        "mistral_OCR",
        "02_01_2023__Rosenblatt_Securities__Inc___ABC_News__AI__Bandwidth_and_Compute_in_the_Last_Week__Mr__Hans_Mosesmann.pdf"
    )
    
    # Check if file exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found at {pdf_path}")
        print("Please update the pdf_path variable in main() to point to your PDF file.")
        return
    
    print("="*80)
    print("Docling OCR Test Script")
    print("="*80)
    print()
    
    # Process the PDF
    try:
        document_data = convert_pdf_to_chunks(
            pdf_path,
            chunk_size_words=300,
            force_full_page_ocr=True,
            do_table_structure=True,
        )
    except Exception as e:
        print(f"❌ Error processing document: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Docling is installed: pip install docling")
        print("2. EasyOCR is used by default (included with Docling)")
        print("3. Check that your PDF file exists and is readable")
        print("4. If GPU is unavailable, processing may take longer")
        return
    
    # Create output filename - save in docling_ocr directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_filename = f"{pdf_name}_docling_chunks.json"
    output_path = os.path.join(script_dir, output_filename)
    
    # Save complete output to JSON file (including full markdown)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(document_data, f, indent=2, ensure_ascii=False)
    
    # Also save the full markdown separately for convenience
    markdown_filename = f"{pdf_name}_docling_full.md"
    markdown_path = os.path.join(script_dir, markdown_filename)
    with open(markdown_path, 'w', encoding='utf-8') as f:
        f.write(document_data["full_markdown"])
    
    print()
    print("="*80)
    print("Processing Summary")
    print("="*80)
    print(f"✅ OCR processing completed!")
    print(f"📄 Document: {document_data['document_info']['filename']}")
    print(f"📊 Estimated pages: {document_data['document_info']['total_pages']}")
    print(f"🔢 Total chunks: {document_data['document_info']['total_chunks']}")
    print(f"📝 Total characters: {document_data['document_info']['total_characters']:,}")
    print(f"💾 Chunks saved to: {output_filename}")
    print(f"📖 Full markdown saved to: {markdown_filename}")
    
    # Show preview of first few chunks
    print()
    print("="*80)
    print("Preview of First 3 Chunks")
    print("="*80)
    print()
    
    for chunk_info in document_data['chunks'][:3]:
        snippet = textwrap.shorten(
            chunk_info["content"],
            width=150,
            placeholder="…"
        )
        print(f"Chunk #{chunk_info['chunk_id']}:")
        print(f"  Title      : {chunk_info['title']}")
        print(f"  Page (est.): {chunk_info['page_number']}")
        print(f"  Word Count : {chunk_info['word_count']}")
        print(f"  Content    : {snippet}")
        print("  " + "-"*76)
    
    print()
    print(f"📁 Full content available in:")
    print(f"   - Chunks: {output_filename}")
    print(f"   - Markdown: {markdown_filename}")
    print()


if __name__ == "__main__":
    main()

