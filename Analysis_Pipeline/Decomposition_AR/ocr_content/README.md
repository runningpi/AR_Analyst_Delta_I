# OCR Content Directory

This directory contains OCR extraction results from analyst reports.

## Structure

Each analyst report gets its own subdirectory named after the PDF filename:

```
ocr_content/
├── 02_01_2023_Rosenblatt/
│   ├── extracted_text.md        # Full markdown text from Docling
│   ├── extracted_sections.json  # Structured sections with sentences
│   └── metadata.json             # Extraction metadata
├── another_report/
│   ├── extracted_text.md
│   ├── extracted_sections.json
│   └── metadata.json
...
```

## Files Description

### `extracted_text.md`
- Full text extracted from PDF using Docling OCR
- Markdown format preserving document structure
- Includes headers, tables, and formatting

### `extracted_sections.json`
- Structured JSON with sections and sentences
- Format:
  ```json
  {
    "Section Name": [
      "Sentence 1",
      "Sentence 2",
      ...
    ],
    ...
  }
  ```

### `metadata.json`
- Extraction metadata including:
  - PDF filename and path
  - Extraction timestamp
  - Statistics (sections count, sentences count, character count)
  - Processing options (GPU usage, etc.)
  - List of section names

## Usage

These files are automatically generated when the pipeline processes an analyst report with Docling OCR.

To reuse extracted content without re-processing:
```python
from Decomposition_AR.text_mangement_utils import TextManager

tm = TextManager()
sections = tm.load_sections_from_json("ocr_content/02_01_2023_Rosenblatt/extracted_sections.json")
```

## Benefits

1. **Avoid Re-processing**: OCR is slow; save results for future use
2. **Manual Review**: Inspect markdown for OCR quality
3. **Debugging**: Compare different processing stages
4. **Archival**: Keep original OCR output separate from analysis results

