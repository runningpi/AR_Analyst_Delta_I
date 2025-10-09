"""
compare_ocr_systems.py – Compare Mistral OCR vs Docling OCR side-by-side

This script processes the same PDF with both OCR systems and provides
a comparison of results, processing time, and quality metrics.

Usage:
$ python compare_ocr_systems.py <pdf_path>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

# Try to import both systems
mistral_available = False
docling_available = False

try:
    from test import convert_pdf_to_chunks as mistral_convert
    mistral_available = True
except ImportError as e:
    print(f"⚠️  Mistral OCR not available: {e}")

try:
    from test_docling import convert_pdf_to_chunks as docling_convert
    docling_available = True
except ImportError as e:
    print(f"⚠️  Docling OCR not available: {e}")


def process_with_mistral(pdf_path: str) -> Tuple[Optional[Dict], float, Optional[str]]:
    """
    Process PDF with Mistral OCR.
    Returns: (result_dict, processing_time_seconds, error_message)
    """
    if not mistral_available:
        return None, 0, "Mistral dependencies not installed"
    
    try:
        start = time.time()
        import asyncio
        result = asyncio.run(mistral_convert(pdf_path))
        elapsed = time.time() - start
        return result, elapsed, None
    except Exception as e:
        return None, 0, str(e)


def process_with_docling(pdf_path: str) -> Tuple[Optional[Dict], float, Optional[str]]:
    """
    Process PDF with Docling OCR.
    Returns: (result_dict, processing_time_seconds, error_message)
    """
    if not docling_available:
        return None, 0, "Docling dependencies not installed"
    
    try:
        start = time.time()
        result = docling_convert(pdf_path)
        elapsed = time.time() - start
        return result, elapsed, None
    except Exception as e:
        return None, 0, str(e)


def analyze_results(mistral_data: Optional[Dict], docling_data: Optional[Dict]) -> Dict:
    """
    Analyze and compare the results from both OCR systems.
    """
    comparison = {
        "mistral": {},
        "docling": {},
        "differences": {}
    }
    
    if mistral_data:
        info = mistral_data["document_info"]
        chunks = mistral_data["chunks"]
        total_words = sum(c["word_count"] for c in chunks)
        total_chars = sum(len(c["content"]) for c in chunks)
        
        comparison["mistral"] = {
            "available": True,
            "total_chunks": len(chunks),
            "total_words": total_words,
            "total_characters": total_chars,
            "avg_chunk_size": total_words // len(chunks) if chunks else 0,
            "pages": info.get("total_pages", 0),
        }
    else:
        comparison["mistral"] = {"available": False}
    
    if docling_data:
        info = docling_data["document_info"]
        chunks = docling_data["chunks"]
        total_words = sum(c["word_count"] for c in chunks)
        total_chars = info.get("total_characters", 0)
        
        comparison["docling"] = {
            "available": True,
            "total_chunks": len(chunks),
            "total_words": total_words,
            "total_characters": total_chars,
            "avg_chunk_size": total_words // len(chunks) if chunks else 0,
            "pages": info.get("total_pages", 0),
        }
    else:
        comparison["docling"] = {"available": False}
    
    # Calculate differences
    if mistral_data and docling_data:
        m = comparison["mistral"]
        d = comparison["docling"]
        
        comparison["differences"] = {
            "chunks_diff": d["total_chunks"] - m["total_chunks"],
            "words_diff": d["total_words"] - m["total_words"],
            "words_diff_pct": ((d["total_words"] - m["total_words"]) / m["total_words"] * 100) if m["total_words"] > 0 else 0,
            "chars_diff": d["total_characters"] - m["total_characters"],
            "chars_diff_pct": ((d["total_characters"] - m["total_characters"]) / m["total_characters"] * 100) if m["total_characters"] > 0 else 0,
        }
    
    return comparison


def print_comparison_report(
    pdf_path: str,
    mistral_result: Tuple[Optional[Dict], float, Optional[str]],
    docling_result: Tuple[Optional[Dict], float, Optional[str]],
):
    """Print a detailed comparison report."""
    
    mistral_data, mistral_time, mistral_error = mistral_result
    docling_data, docling_time, docling_error = docling_result
    
    print("\n" + "="*80)
    print("OCR SYSTEM COMPARISON REPORT")
    print("="*80)
    print(f"\n📄 Document: {os.path.basename(pdf_path)}")
    print(f"📏 File size: {os.path.getsize(pdf_path) / 1024 / 1024:.2f} MB")
    
    # Mistral Results
    print("\n" + "-"*80)
    print("🤖 MISTRAL AI OCR")
    print("-"*80)
    if mistral_error:
        print(f"❌ Error: {mistral_error}")
    elif mistral_data:
        info = mistral_data["document_info"]
        print(f"✅ Success")
        print(f"   Processing time: {mistral_time:.2f} seconds")
        print(f"   Pages: {info.get('total_pages', 'N/A')}")
        print(f"   Chunks: {info['total_chunks']}")
        print(f"   Model: {info.get('processing_model', 'N/A')}")
        print(f"   Total words: {sum(c['word_count'] for c in mistral_data['chunks']):,}")
        print(f"   Total characters: {sum(len(c['content']) for c in mistral_data['chunks']):,}")
    else:
        print("⚠️  Not available")
    
    # Docling Results
    print("\n" + "-"*80)
    print("📚 DOCLING OCR")
    print("-"*80)
    if docling_error:
        print(f"❌ Error: {docling_error}")
    elif docling_data:
        info = docling_data["document_info"]
        print(f"✅ Success")
        print(f"   Processing time: {docling_time:.2f} seconds")
        print(f"   Pages (estimated): {info.get('total_pages', 'N/A')}")
        print(f"   Chunks: {info['total_chunks']}")
        print(f"   OCR backend: {info.get('ocr_backend', 'N/A')}")
        print(f"   Table extraction: {info.get('table_extraction_enabled', False)}")
        print(f"   Total words: {sum(c['word_count'] for c in docling_data['chunks']):,}")
        print(f"   Total characters: {info.get('total_characters', 'N/A'):,}")
    else:
        print("⚠️  Not available")
    
    # Comparison
    if mistral_data and docling_data:
        comparison = analyze_results(mistral_data, docling_data)
        diff = comparison["differences"]
        
        print("\n" + "-"*80)
        print("📊 COMPARISON")
        print("-"*80)
        
        # Processing time
        if mistral_time > 0 and docling_time > 0:
            time_diff = docling_time - mistral_time
            time_diff_pct = (time_diff / mistral_time) * 100
            faster = "Docling" if time_diff < 0 else "Mistral"
            print(f"   Processing time:")
            print(f"     Mistral: {mistral_time:.2f}s")
            print(f"     Docling: {docling_time:.2f}s")
            print(f"     {faster} was {abs(time_diff):.2f}s ({abs(time_diff_pct):.1f}%) faster")
        
        # Content comparison
        print(f"\n   Content extraction:")
        print(f"     Chunks difference: {diff['chunks_diff']:+,}")
        print(f"     Words difference: {diff['words_diff']:+,} ({diff['words_diff_pct']:+.1f}%)")
        print(f"     Characters difference: {diff['chars_diff']:+,} ({diff['chars_diff_pct']:+.1f}%)")
        
        # Quality indicators
        print(f"\n   Quality indicators:")
        if abs(diff['words_diff_pct']) < 5:
            print(f"     ✅ Very similar content extraction ({abs(diff['words_diff_pct']):.1f}% difference)")
        elif abs(diff['words_diff_pct']) < 15:
            print(f"     ⚠️  Moderate difference in content extraction ({abs(diff['words_diff_pct']):.1f}% difference)")
        else:
            print(f"     ❌ Significant difference in content extraction ({abs(diff['words_diff_pct']):.1f}% difference)")
    
    # Recommendations
    print("\n" + "-"*80)
    print("💡 RECOMMENDATIONS")
    print("-"*80)
    
    if mistral_data and docling_data:
        if docling_time < mistral_time:
            print("   • Docling was faster for this document")
        else:
            print("   • Mistral was faster for this document")
        
        if abs(diff['words_diff_pct']) < 5:
            print("   • Both systems extracted similar content")
            print("   • Consider using Docling for offline/privacy needs")
            print("   • Consider using Mistral for cloud convenience")
        else:
            more_content = "Docling" if diff['words_diff'] > 0 else "Mistral"
            print(f"   • {more_content} extracted more content")
            print("   • Manually review outputs to assess quality")
    elif mistral_data:
        print("   • Only Mistral OCR is available")
        print("   • Consider installing Docling for offline processing")
    elif docling_data:
        print("   • Only Docling OCR is available")
        print("   • Consider setting up Mistral API for cloud processing")
    else:
        print("   • Neither OCR system is available")
        print("   • Install required dependencies")
    
    print("\n" + "="*80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Compare Mistral OCR and Docling OCR on the same PDF"
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        help="Path to the PDF file to process"
    )
    args = parser.parse_args()
    
    # Default PDF path
    if not args.pdf_path:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(
            script_dir,
            "02_01_2023__Rosenblatt_Securities__Inc___ABC_News__AI__Bandwidth_and_Compute_in_the_Last_Week__Mr__Hans_Mosesmann.pdf"
        )
    else:
        pdf_path = args.pdf_path
    
    # Validate PDF exists
    if not os.path.exists(pdf_path):
        print(f"❌ Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Check if at least one system is available
    if not mistral_available and not docling_available:
        print("❌ Error: Neither Mistral nor Docling OCR is available")
        print("\nInstallation instructions:")
        print("  Mistral: pip install mistralai python-dotenv tenacity")
        print("  Docling: pip install -r requirements_docling.txt")
        sys.exit(1)
    
    # Process with both systems
    print("Processing with available OCR systems...")
    print("This may take a few minutes depending on document size.\n")
    
    mistral_result = (None, 0, "Not processed")
    docling_result = (None, 0, "Not processed")
    
    if mistral_available:
        print("🤖 Processing with Mistral OCR...")
        mistral_result = process_with_mistral(pdf_path)
    
    if docling_available:
        print("📚 Processing with Docling OCR...")
        docling_result = process_with_docling(pdf_path)
    
    # Print comparison report
    print_comparison_report(pdf_path, mistral_result, docling_result)
    
    # Optionally save comparison to JSON
    output_dir = os.path.dirname(pdf_path)
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    comparison_file = os.path.join(output_dir, f"{pdf_name}_ocr_comparison.json")
    
    mistral_data, mistral_time, mistral_error = mistral_result
    docling_data, docling_time, docling_error = docling_result
    
    comparison_data = {
        "pdf_path": pdf_path,
        "file_size_mb": os.path.getsize(pdf_path) / 1024 / 1024,
        "mistral": {
            "available": mistral_available,
            "processing_time": mistral_time,
            "error": mistral_error,
            "success": mistral_data is not None,
        },
        "docling": {
            "available": docling_available,
            "processing_time": docling_time,
            "error": docling_error,
            "success": docling_data is not None,
        }
    }
    
    if mistral_data and docling_data:
        comparison_data["comparison"] = analyze_results(mistral_data, docling_data)
    
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison_data, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Comparison saved to: {os.path.basename(comparison_file)}\n")


if __name__ == "__main__":
    main()

