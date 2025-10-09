"""
 test.py – OCR a local PDF with Mistral, chunk the text, and show a preview

 $ pip install mistralai python-dotenv tenacity
 $ echo "MISTRAL_API_KEY=sk-..." > .env
 $ python test.py
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import tempfile
import textwrap
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
from mistralai import Mistral
from mistralai.models import SDKError
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

# ---------------------------------------------------------------------------
#  Initialisation
# ---------------------------------------------------------------------------
load_dotenv()  # pull variables from .env (expects MISTRAL_API_KEY)

# API key loaded from environment


# ---------------------------------------------------------------------------
#  Retry helpers
# ---------------------------------------------------------------------------

def _is_retryable(exc: BaseException) -> bool:
    """Return **True** for 5xx SDK errors so tenacity will retry."""
    return isinstance(exc, SDKError) and getattr(exc, "status_code", 0) >= 500


def _client(api_key: str | None = None) -> Mistral:
    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("Set MISTRAL_API_KEY in .env or pass api_key=")
    return Mistral(api_key=api_key)


# ---------------------------------------------------------------------------
#  Preferred path: upload file → signed URL → OCR
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def ocr_pdf_via_upload(
    pdf_path: str,
    *,
    api_key: Optional[str] = None,
    model: str = "mistral-ocr-latest",
):
    """Upload *pdf_path*, obtain a signed URL, then OCR it."""
    client = _client(api_key)

    uploaded = client.files.upload(
        file={
            "file_name": os.path.basename(pdf_path),
            "content": open(pdf_path, "rb"),
        },
        purpose="ocr",  # type: ignore[arg-type] – SDK expects str
    )

    signed = client.files.get_signed_url(file_id=uploaded.id)

    return client.ocr.process(
        model=model,
        document={"type": "document_url", "document_url": signed.url},
    )


# ---------------------------------------------------------------------------
#  Optional: start from Base‑64 string, write temp PDF, then call ↑
# ---------------------------------------------------------------------------

def ocr_pdf_from_base64(
    pdf_b64: str,
    *,
    api_key: Optional[str] = None,
    model: str = "mistral-ocr-latest",
):
    """Decode *pdf_b64* → temp file → OCR exactly as for a normal PDF."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
        tf.write(base64.b64decode(pdf_b64))
        tmp_path = tf.name

    try:
        return ocr_pdf_via_upload(tmp_path, api_key=api_key, model=model)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
#  High‑level: PDF → chunked Markdown
# ---------------------------------------------------------------------------

async def convert_pdf_to_chunks(
    pdf_path: str,
    *,
    chunk_size_words: int = 300,
    api_key: Optional[str] = None,
) -> Dict:
    """OCR *pdf_path* and break the Markdown into ≈*chunk_size_words* blocks.
    Returns a complete document structure with metadata and chunks.
    """
    print(f"Starting OCR processing for: {os.path.basename(pdf_path)}")
    
    ocr_response = await asyncio.to_thread(
        ocr_pdf_via_upload,
        pdf_path,
        api_key=api_key,
    )

    chunks: List[Dict] = []
    chunk_id = 1
    
    for page_idx, page in enumerate(ocr_response.pages, start=1):
        print(f"Processing page {page_idx}/{len(ocr_response.pages)}")
        words = page.markdown.split()
        
        for start in range(0, len(words), chunk_size_words):
            block = words[start : start + chunk_size_words]
            if block:
                chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "title": block[0] if len(block[0]) <= 100 else block[0][:100] + "...",
                        "page_number": page_idx,
                        "content": " ".join(block),
                        "word_count": len(block),
                        "start_word_index": start,
                        "end_word_index": min(start + chunk_size_words - 1, len(words) - 1)
                    }
                )
                chunk_id += 1

    # Create complete document structure
    document_data = {
        "document_info": {
            "filename": os.path.basename(pdf_path),
            "filepath": pdf_path,
            "processed_at": datetime.now().isoformat(),
            "total_pages": len(ocr_response.pages),
            "total_chunks": len(chunks),
            "chunk_size_words": chunk_size_words,
            "processing_model": "mistral-ocr-latest"
        },
        "chunks": chunks
    }

    return document_data


# ---------------------------------------------------------------------------
#  Demo / CLI entry‑point
# ---------------------------------------------------------------------------

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(script_dir, "02_01_2023__Rosenblatt_Securities__Inc___ABC_News__AI__Bandwidth_and_Compute_in_the_Last_Week__Mr__Hans_Mosesmann.pdf")

    # Process the PDF
    document_data = asyncio.run(convert_pdf_to_chunks(pdf_path))
    
    # Create output filename
    pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_filename = f"{pdf_name}_ocr_chunks.json"
    output_path = os.path.join(script_dir, output_filename)
    
    # Save to JSON file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(document_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ OCR processing completed!")
    print(f"📄 Document: {document_data['document_info']['filename']}")
    print(f"📊 Total pages: {document_data['document_info']['total_pages']}")
    print(f"🔢 Total chunks: {document_data['document_info']['total_chunks']}")
    print(f"💾 Output saved to: {output_filename}")
    
    # Show preview of first few chunks
    print("\n=== Preview of first 3 chunks ===\n")
    for chunk_info in document_data['chunks'][:3]:
        snippet = textwrap.shorten(chunk_info["content"], width=150, placeholder="…")
        print(f"Chunk #{chunk_info['chunk_id']}:")
        print(f"  Title      : {chunk_info['title']}")
        print(f"  Page       : {chunk_info['page_number']}")
        print(f"  Word Count : {chunk_info['word_count']}")
        print(f"  Content    : {snippet}")
        print("  --")
    
    print(f"\n📁 Full content available in: {output_filename}\n")


if __name__ == "__main__":
    main()
