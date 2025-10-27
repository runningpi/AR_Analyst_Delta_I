# Evaluation Results Output

This directory contains cached LLM evaluation results for analyst report sentences.

## Structure

```
output/
├── [PDF_NAME]/
│   ├── evaluations.json    # LLM evaluation results
│   └── metadata.json        # Metadata about the evaluation process
└── README.md
```

## Files

### evaluations.json
Contains the evaluation results for each section of the analyst report:
- Sentence text
- Section name
- Classification source
- Evidence texts from the Knowledge Base
- Evaluation label (Supported, Partially Supported, Not Supported, Contradicted, No Evidence)
- Reasoning from the LLM

### metadata.json
Contains metadata about the evaluation process:
- PDF filename and path
- Timestamp of when evaluation was performed
- Total sections and sentences evaluated
- Evaluation label distribution (how many sentences got each label)
- LLM model used for evaluation

## Caching

The pipeline automatically caches evaluation results to avoid redundant LLM API calls:
- **First run**: Calls LLM for each sentence and saves results
- **Subsequent runs**: Loads cached results instantly
- **Cache invalidation**: Delete the document directory to force re-evaluation

## Purpose

This caching mechanism:
- **Saves money**: Avoids costly LLM API calls on subsequent runs
- **Saves time**: Instant evaluation retrieval from cache
- **Ensures consistency**: Same evaluation results across multiple analysis runs
- **Enables debugging**: Easy to review LLM evaluation decisions
- **Supports iteration**: Can modify analysis/reporting without re-running expensive evaluations

## Evaluation Labels

- **Supported**: Evidence fully backs the claim in the sentence
- **Partially Supported**: Evidence partially backs the claim, but some aspects are missing
- **Not Supported**: Evidence doesn't back the claim
- **Contradicted**: Evidence directly contradicts the claim
- **No Evidence**: No relevant evidence was found in the knowledge base
- **Unknown**: Evaluation failed or could not be determined

