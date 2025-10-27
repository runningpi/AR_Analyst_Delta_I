# Classified Sentences Cache Directory

This directory contains cached classification results for analyst reports.

## Structure

Each analyst report gets its own subdirectory named after the PDF filename:

```
classified_sentences/
├── 02_01_2023_Rosenblatt/
│   ├── classified_sentences.json    # Classified sentences
│   └── metadata.json                 # Classification metadata
├── another_report/
│   ├── classified_sentences.json
│   └── metadata.json
...
```

## Files Description

### `classified_sentences.json`
- Structured JSON with classified sentences
- Format:
  ```json
  {
    "Overview": [
      {
        "sentence": "Company posted strong results...",
        "source": "corporate_information"
      },
      {
        "sentence": "We maintain our BUY rating...",
        "source": "analyst_interpretation"
      }
    ],
    "Investment Thesis": [...]
  }
  ```

### `metadata.json`
- Classification metadata:
  ```json
  {
    "pdf_file": "/full/path/to/file.pdf",
    "pdf_filename": "02_01_2023_Rosenblatt.pdf",
    "classified_at": "2025-10-09T17:00:00",
    "total_sections": 8,
    "total_sentences": 145,
    "source_distribution": {
      "corporate_information": 65,
      "market_information": 25,
      "analyst_interpretation": 50,
      "other": 5
    },
    "model_used": "gpt-4o-mini",
    "batch_size": 10
  }
  ```

## Classification Sources

Sentences are classified into:
- **corporate_information**: Company financials, products, strategies, official guidance
- **market_information**: Competitors, industry trends, market context
- **analyst_interpretation**: Judgments, forecasts, analyst conclusions
- **other**: Miscellaneous content

## Caching Behavior

### First Run (Fresh Classification)
1. Check for cached classifications
2. Not found → Classify with GPT (2-5 minutes)
3. Save to cache directory
4. Continue pipeline

### Subsequent Runs (Cached)
1. Check for cached classifications
2. Found! → Load from cache (< 1 second)
3. Skip GPT classification entirely
4. Continue pipeline

## Performance Impact

| Scenario | Time | Cost |
|----------|------|------|
| First run (no cache) | 2-5 min | API costs |
| Cached run | < 1 sec | FREE |
| Savings | 99%+ faster | 100% cost savings |

## Usage

### Automatic (Pipeline)
Caching happens automatically when you run the pipeline:

```bash
python analyse_delta_i_for_one_AR.py
```

The pipeline will:
1. Check cache first
2. Use cached results if available
3. Only classify if cache doesn't exist

### Manual Reuse
Load previously classified sentences:

```python
from Decomposition_AR.text_mangement_utils import ClassificationManager

cm = ClassificationManager()
classified = cm.load_classified_sentences(
    "Decomposition_AR/output/classified_sentences/02_01_2023_Rosenblatt/classified_sentences.json"
)
```

### Programmatic
```python
from pipeline import ARAnalysisPipeline

pipeline = ARAnalysisPipeline(config)

# Use cache (default)
classified = pipeline.classify_sentences(sections, pdf_name="report", use_cached=True)

# Force fresh classification
classified = pipeline.classify_sentences(sections, pdf_name="report", use_cached=False)
```

## Cache Invalidation

### When to Clear Cache

Clear cache if:
- Re-extracted PDF with different content
- Changed classification model
- Changed classification prompts
- Testing classification logic

### How to Clear

**Clear specific report:**
```bash
rm -rf Decomposition_AR/output/classified_sentences/02_01_2023_Rosenblatt/
```

**Clear all cache:**
```bash
rm -rf Decomposition_AR/output/classified_sentences/*/
```

## Benefits

1. **Speed**: 2-5 minutes → < 1 second
2. **Cost**: No repeated API calls to OpenAI
3. **Consistency**: Same classifications every time
4. **Reliability**: No risk of API failures on reruns
5. **Debugging**: Compare different classification approaches

## Log Messages

### Cache Hit:
```
INFO - ✓ Found cached classified sentences at: ...
INFO - Loading classifications from cache (skipping classification)...
INFO - ✓ Loaded classifications for 145 sentences from cache
INFO -   Originally classified: 2025-10-09T16:30:00
```

### Cache Miss:
```
INFO - No cached classifications found. Running classification...
INFO - Classifying 145 sentences...
INFO - Classification complete. Total sentences classified: 145
INFO - Saved classified sentences to cache: ...
```

## Integration

This cache integrates seamlessly with:
- **OCR Cache**: Uses OCR-extracted sentences
- **Pipeline**: Automatic cache management
- **Checkpoints**: Can resume from classification checkpoint

## Example Workflow

### Complete First Run:
```bash
python analyse_delta_i_for_one_AR.py
```
- OCR: 10-20 min (or load from cache)
- Classification: 2-5 min → **saves to cache**
- Continue pipeline...

### Second Run:
```bash
python analyse_delta_i_for_one_AR.py
```
- OCR: < 1 sec (from cache)
- Classification: < 1 sec → **loads from cache**
- Continue pipeline...

**Total time saved**: 12-25 minutes → < 2 seconds!

