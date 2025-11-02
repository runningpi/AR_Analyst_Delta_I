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
│ PHASE 2: SNIPPET EXTRACTION & CLASSIFICATION                        │
│                                                                      │
│  ClassificationService (GPT-4o-mini)                                │
│  ├─ Extract knowledge snippets from sentences                       │
│  ├─ Batch processing (10 sentences/batch)                          │
│  ├─ Classify each snippet into 4 categories:                       │
│  │   1. CLAIM TYPE:                                                 │
│  │      • assertion (verifiable statement)                         │
│  │      • hypothesis (non-verifiable statement)                    │
│  │      • other                                                     │
│  │   2. SUBJECT SCOPE:                                              │
│  │      • company (about specific firm)                            │
│  │      • market (about industry/sector)                            │
│  │      • other                                                     │
│  │   3. CONTENT TYPE:                                               │
│  │      • quantitative (includes numbers)                           │
│  │      • qualitative (descriptive)                                  │
│  │      • other                                                     │
│  │   4. CONTENT RELEVANCE:                                          │
│  │      • company_relevant                                          │
│  │      • template_boilerplate                                      │
│  │      • other                                                     │
│  └─ JSON response parsing with confidence scores                   │
│                                                                      │
│  Output: {                                                           │
│    "overview": [                                                     │
│      {                                                               │
│        "snippet": "...",                                            │
│        "claim_type": "assertion",                                   │
│        "subject_scope": "company",                                 │
│        "sentence_type": "quantitative",                             │
│        "content_relevance": "company_relevant",                     │
│        ...                                                           │
│      }, ...                                                          │
│    ]                                                                 │
│  }                                                                   │
└────────┬─────────────────────────────────────────────────────────────┘
         │
         ▼
         │  classified_snippets.json
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
│  ├─ Filter: Only process company_relevant snippets                 │
│  │   └─ Exclude template_boilerplate snippets                       │
│  ├─ For each company_relevant snippet:                             │
│  │   ├─ Query KB with snippet text                                  │
│  │   ├─ Retrieve top-5 relevant segments                           │
│  │   └─ Extract evidence text                                       │
│  └─ Progress tracking                                                │
│                                                                      │
│  Flow:                                                               │
│  Snippets ──► [Filter company_relevant] ──► [Query KB] ──►          │
│    Top-5 Segments ──► Evidence Texts                                 │
│                                                                      │
│  Output: {                                                           │
│    "overview": [                                                     │
│      {                                                               │
│        "snippet": "...",                                            │
│        "claim_type": "assertion",                                   │
│        "subject_scope": "company",                                 │
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
│        "claim_type": "assertion",                                   │
│        "subject_scope": "company",                                 │
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
│  │   ├─ Total sentences (company_relevant only)                    │
│  │   ├─ Total template_boilerplate (excluded)                       │
│  │   ├─ By evaluation label                                         │
│  │   ├─ By claim_type (assertion/hypothesis/other)                 │
│  │   ├─ By subject_scope (company/market/other)                    │
│  │   └─ By section                                                  │
│  │                                                                   │
│  ├─ Coverage Analysis (company_relevant only)                       │
│  │   ├─ Covered (Supported + Partially Supported)                  │
│  │   ├─ Not Covered (Not Supported + No Evidence)                  │
│  │   └─ Contradicted                                                │
│  │                                                                   │
│  ├─ Coverage Breakdowns                                              │
│  │   ├─ By claim_type (assertion vs hypothesis)                    │
│  │   ├─ By subject_scope (company vs market vs other)              │
│  │   ├─ By section and claim_type/subject_scope                    │
│  │   └─ By section (crosstab)                                       │
│  │                                                                   │
│  └─ Search & Filter                                                  │
│      ├─ By section                                                   │
│      ├─ By evaluation label                                          │
│      ├─ By claim_type                                                │
│      └─ By subject_scope                                             │
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
Classified Snippets (List[{
    snippet,
    claim_type,      // assertion/hypothesis/other
    subject_scope,   // company/market/other
    sentence_type,   // quantitative/qualitative/other
    content_relevance  // company_relevant/template_boilerplate/other
}])
    ↓
Filter: Only company_relevant snippets
    ↓
Query Results (List[{
    snippet,
    claim_type,
    subject_scope,
    evidence
}])
    ↓
Evaluations (List[{
    snippet,
    claim_type,
    subject_scope,
    evidence,
    evaluation,
    reason
}])
    ↓
Analysis (Statistics, Reports, Insights)
    ├─ Coverage by claim_type
    ├─ Coverage by subject_scope
    └─ Coverage by section and classification
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

By Classification:
├─ Claim Type:
│   ├─ Assertions: Usually high support rate (verifiable claims)
│   └─ Hypotheses: Lower support rate (forecasts, expectations)
├─ Subject Scope:
│   ├─ Company: Usually high support rate (firm-specific data)
│   ├─ Market: Moderate support rate (industry data)
│   └─ Other: Varies (macroeconomic factors)
└─ Content Relevance:
    ├─ Company Relevant: Included in analysis
    └─ Template Boilerplate: Excluded from analysis
```

