# AR Analyst Delta I - Workflow Diagram

## Complete Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    AR ANALYST DELTA I PIPELINE                       │
│                       ΔI = ΔAR - ΔΣ                                  │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Analyst Report  │
│   (PDF/Text)     │
└────────┬─────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: TEXT EXTRACTION & PARSING                                  │
│                                                                      │
│  DoclingParser                                                       │
│  ├─ Extract text from PDF (Docling OCR)                            │
│  ├─ TextCleaner: Normalize whitespace                               │
│  └─ SentenceSplitter: Split into sentences                          │
│                                                                      │
│  Output: { "overview": ["sent1", "sent2", ...], ... }              │
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
         │  extracted_sentences.json
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: SENTENCE CLASSIFICATION                                     │
│                                                                      │
│  ClassificationService (GPT-4o-mini)                                │
│  ├─ Batch processing (10 sentences/batch)                          │
│  ├─ Classify into:                                                  │
│  │   • corporate_information                                        │
│  │   • market_information                                           │
│  │   • analyst_interpretation                                       │
│  │   • other                                                        │
│  └─ JSON response parsing                                           │
│                                                                      │
│  Output: { "overview": [{"sentence": "...", "source": "..."}, ...] }│
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
         │  classified_sentences.json
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: KNOWLEDGE BASE SETUP                                        │
│                                                                      │
│  KnowledgeBaseManager (DS-RAG)                                      │
│  ├─ Load company documents (10-Q, 8-K, transcripts, etc.)          │
│  ├─ Chunk documents (200 tokens)                                    │
│  ├─ Generate embeddings (OpenAI)                                    │
│  ├─ Store in knowledge base                                         │
│  └─ Initialize Cohere reranker (optional)                           │
│                                                                      │
│  Input:                                                              │
│  ┌────────────────────────┐                                         │
│  │ Company Documents      │                                         │
│  ├────────────────────────┤                                         │
│  │ • 10-Q Reports        │                                         │
│  │ • 8-K Filings         │                                         │
│  │ • Earnings Transcripts│                                         │
│  │ • Presentations       │                                         │
│  │ • Press Releases      │                                         │
│  └────────────────────────┘                                         │
│           │                                                          │
│           ▼                                                          │
│  ┌────────────────────────┐                                         │
│  │  Knowledge Base (KB)   │                                         │
│  │  ├─ Chunks            │                                         │
│  │  ├─ Embeddings        │                                         │
│  │  └─ Metadata          │                                         │
│  └────────────────────────┘                                         │
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: RAG QUERY & MATCHING                                        │
│                                                                      │
│  SentenceMatcher                                                     │
│  ├─ For each sentence:                                              │
│  │   ├─ Query KB with sentence                                      │
│  │   ├─ Retrieve top-5 relevant segments                           │
│  │   └─ Extract evidence text                                       │
│  └─ Progress tracking                                                │
│                                                                      │
│  Flow:                                                               │
│  Sentence ──► [Query KB] ──► Top-5 Segments ──► Evidence Texts     │
│                                                                      │
│  Output: {                                                           │
│    "overview": [                                                     │
│      {                                                               │
│        "sentence": "...",                                           │
│        "source": "corporate_information",                           │
│        "evidence": ["evidence1", "evidence2", ...]                  │
│      }, ...                                                          │
│    ]                                                                 │
│  }                                                                   │
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
         │  query_results.json
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 5: LLM EVALUATION                                              │
│                                                                      │
│  EvaluationService (GPT-4o-mini)                                    │
│  ├─ For each sentence + evidence:                                   │
│  │   ├─ Create evaluation prompt                                    │
│  │   ├─ Call GPT for evaluation                                     │
│  │   └─ Parse structured response                                   │
│  │                                                                   │
│  ├─ Evaluation Labels:                                              │
│  │   • Supported           ✓ Fully backed by evidence              │
│  │   • Partially Supported ≈ Partially backed                       │
│  │   • Not Supported       ✗ No backing evidence                    │
│  │   • Contradicted        ⚠ Conflicts with evidence                │
│  │   • No Evidence         ∅ No relevant evidence found             │
│  │                                                                   │
│  └─ Generate reasoning                                               │
│                                                                      │
│  Output: {                                                           │
│    "overview": [                                                     │
│      {                                                               │
│        "sentence": "...",                                           │
│        "source": "...",                                             │
│        "evidence": [...],                                           │
│        "evaluation": "Supported",                                   │
│        "reason": "The KB explicitly states..."                      │
│      }, ...                                                          │
│    ]                                                                 │
│  }                                                                   │
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
         │  evaluations.json
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 6: ANALYSIS & REPORTING                                        │
│                                                                      │
│  EvaluationAnalyzer                                                  │
│  ├─ Overall Statistics                                              │
│  │   ├─ Total sentences                                             │
│  │   ├─ By evaluation label                                         │
│  │   ├─ By source type                                              │
│  │   └─ By section                                                  │
│  │                                                                   │
│  ├─ Coverage Analysis                                                │
│  │   ├─ Covered (Supported + Partially Supported)                  │
│  │   ├─ Not Covered (Not Supported + No Evidence)                  │
│  │   └─ Contradicted                                                │
│  │                                                                   │
│  ├─ Breakdowns                                                       │
│  │   ├─ By section (crosstab)                                       │
│  │   └─ By source type (crosstab)                                   │
│  │                                                                   │
│  └─ Search & Filter                                                  │
│      ├─ By section                                                   │
│      ├─ By evaluation label                                          │
│      └─ By source type                                               │
│                                                                      │
│  ReportGenerator                                                     │
│  └─ Generate human-readable text report                             │
│                                                                      │
│  Outputs:                                                            │
│  ├─ statistics.json          - Overall stats                         │
│  ├─ coverage_summary.json    - Coverage metrics                      │
│  └─ analysis_report.txt      - Readable report                       │
└─────────────────────────────────────────────────────────────────────┘

                              ▼
                              
┌─────────────────────────────────────────────────────────────────────┐
│                         FINAL RESULTS                                │
│                                                                      │
│  Delta I (ΔI) = Novel Insights                                      │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Coverage Summary                                             │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ Total Sentences: 150                                        │   │
│  │ Covered: 95 (63.3%)                                         │   │
│  │ Not Covered: 45 (30.0%)                                     │   │
│  │ Contradicted: 10 (6.7%)                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Key Insights                                                 │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │ • 30% of sentences have no evidence in company docs         │   │
│  │   → These are NOVEL INSIGHTS from analyst                   │   │
│  │                                                              │   │
│  │ • 6.7% of sentences contradict company data                 │   │
│  │   → Potential analyst errors or different interpretations   │   │
│  │                                                              │   │
│  │ • 63.3% of sentences are supported                          │   │
│  │   → Analyst correctly cited company information             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Checkpoint System

```
Full Pipeline:
  [Extract] → [Classify] → [KB Setup] → [Match] → [Evaluate] → [Analyze]

Resume Points:
  
  Checkpoint: classified
  └─ Skip: [Extract] [Classify]
  └─ Run: [KB Setup] → [Match] → [Evaluate] → [Analyze]
  
  Checkpoint: matched
  └─ Skip: [Extract] [Classify] [KB Setup] [Match]
  └─ Run: [Evaluate] → [Analyze]
  
  Checkpoint: evaluated
  └─ Skip: [Extract] [Classify] [KB Setup] [Match] [Evaluate]
  └─ Run: [Analyze]
```

## Data Flow

```
Input Text
    ↓
Sentences (List[str])
    ↓
Classified Sentences (List[{sentence, source}])
    ↓
Query Results (List[{sentence, source, evidence}])
    ↓
Evaluations (List[{sentence, source, evidence, evaluation, reason}])
    ↓
Analysis (Statistics, Reports, Insights)
```

## Module Dependencies

```
analyse_delta_i_for_one_AR.py
    ↓
core/
├── pipeline.py (main orchestrator)
├── analysis.py (reporting & stats)
└── models/
    ├── sentence.py
    ├── evaluation.py
    └── section.py
    ↓
├── config.py
├── Decomposition_AR/
│   ├── ocr_docling_utils.py
│   ├── text_mangement_utils.py
│   └── classification_service.py
├── RAG_and_knowledgebase/
│   ├── DS_RAG_utils.py
│   └── matching_utils.py
└── Evaluation/
    ├── evaluation_utils.py
    └── evaluation_service.py
```

## Key Metrics

```
Performance Indicators:
├─ Coverage Rate: % of sentences with evidence
├─ Support Rate: % of supported sentences
├─ Novelty Rate: % of unsupported sentences (ΔI)
├─ Contradiction Rate: % of contradicted sentences
└─ Evidence Quality: Average evidence relevance

By Source Type:
├─ Corporate Information: Usually high support rate
├─ Market Information: Moderate support rate
└─ Analyst Interpretation: Lower support rate (expected)
```

