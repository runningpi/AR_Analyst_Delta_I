# AR Analyst Delta I Pipeline

**Calculate the information delta (ΔI) between analyst reports and company-issued documents.**

This pipeline analyzes analyst reports to identify novel insights by comparing them against official company documents. It quantifies what information in analyst reports is truly new versus what's already disclosed by the company.

## 📊 What Does It Do?

The pipeline answers the key question: **"What novel information are analysts providing beyond official company disclosures?"**

**Formula:** `ΔI = ΔAR - ΔΣ`
- **ΔAR**: Information in Analyst Reports
- **ΔΣ**: Information in Company Documents (10-K, 10-Q, earnings calls, presentations)
- **ΔI**: The information delta - novel analyst insights

### Key Outputs

For each analyst report, the pipeline provides:
- **Coverage Analysis**: What % of analyst claims are supported by company documents
- **Novel Insights**: Sentences not found in company documents (potential alpha)
- **Contradictions**: Claims that contradict official company statements
- **Detailed Report**: Section-by-section analysis with evidence

## 🏗️ Pipeline Architecture

The pipeline consists of 5 stages, each with its own caching mechanism:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. OCR & Text Extraction (Decomposition_AR)                     │
│    └─ Extract text from PDF analyst reports using Docling       │
├─────────────────────────────────────────────────────────────────┤
│ 2. Sentence Classification (Decomposition_AR)                   │
│    └─ LLM categorizes sentences: corporate_info, market_info,   │
│       analyst_interpretation, other                             │
├─────────────────────────────────────────────────────────────────┤
│ 3. Knowledge Base Matching (RAG_and_knowledgebase)             │
│    └─ DS-RAG queries company documents for supporting evidence  │
├─────────────────────────────────────────────────────────────────┤
│ 4. LLM Evaluation (Evaluation)                                  │
│    └─ GPT-4 evaluates: Supported, Partially Supported,         │
│       Not Supported, Contradicted, No Evidence                  │
├─────────────────────────────────────────────────────────────────┤
│ 5. Analysis & Reporting (Analysis)                             │
│    └─ Generate comprehensive reports, statistics, and insights  │
└─────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
Analysis_Pipeline/
│
├── 📄 Entry Points & Config
│   ├── analyse_delta_i_for_one_AR.py    # Main entry point
│   ├── config.py                        # Configuration loader
│   ├── settings.config                  # Pipeline settings
│   └── requirements.txt                 # Dependencies
│
├── 🎯 core/                             # Orchestration & Data Models
│   ├── pipeline.py                      # Main pipeline orchestrator
│   ├── analysis.py                      # Analysis & reporting utilities
│   └── models/                          # Data models (Pydantic)
│       ├── sentence.py
│       ├── evaluation.py
│       └── section.py
│
├── 📊 Pipeline Stages
│   ├── Decomposition_AR/                # Stage 1 & 2: OCR & Classification
│   │   ├── ocr_docling_utils.py
│   │   ├── classification_service.py
│   │   ├── text_mangement_utils.py
│   │   ├── ocr_content/[PDF_NAME]/      # 📦 Cached OCR outputs
│   │   └── output/classified_sentences/[PDF_NAME]/  # 📦 Cached classifications
│   │
│   ├── RAG_and_knowledgebase/           # Stage 3: KB Matching
│   │   ├── DS_RAG_utils.py
│   │   ├── matching_utils.py
│   │   ├── kb_storage/                  # Knowledge base vector storage
│   │   └── output/[PDF_NAME]/           # 📦 Cached query results
│   │
│   ├── Evaluation/                      # Stage 4: LLM Evaluation
│   │   ├── evaluation_service.py
│   │   ├── evaluation_utils.py
│   │   └── output/[PDF_NAME]/           # 📦 Cached evaluations
│   │
│   └── Analysis/                        # Stage 5: Final Reports
│       └── output/[PDF_NAME]/           # 📦 Final analysis reports
│
└── 📝 data/                             # Input data
    └── [COMPANY]/[QUARTER]/
        ├── analyst_report/              # Analyst reports (PDFs)
        └── company_reports/             # Company documents (PDFs)
```

## 🚀 Quick Start

### 1. Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file with your API keys:

```bash
cp env_template.txt .env
```

Edit `.env`:
```ini
OPENAI_API_KEY=your_openai_key_here
COHERE_API_KEY=your_cohere_key_here  # Optional, for reranking
```

Edit `settings.config` to point to your data:
```ini
env_file=.env
analyst_report=data/COMPANY/QUARTER/analyst_report/report.pdf
company_data_dir=data/COMPANY/QUARTER/company_reports
```

### 3. Run the Pipeline

```bash
python analyse_delta_i_for_one_AR.py
```

**That's it!** The pipeline will:
1. Extract text from the analyst report (cached after first run)
2. Classify sentences (cached after first run)
3. Build/load knowledge base from company documents
4. Match sentences against KB (cached after first run)
5. Evaluate with LLM (cached after first run)
6. Generate final analysis reports

## 📋 Usage Examples

### Basic Usage

```bash
# Run full pipeline
python analyse_delta_i_for_one_AR.py

# With custom config
python analyse_delta_i_for_one_AR.py --config my_settings.config

# Set log level
python analyse_delta_i_for_one_AR.py --log-level DEBUG
```

### Resume from Checkpoint

Skip completed stages to save time:

```bash
# Resume from classification (skip OCR)
python analyse_delta_i_for_one_AR.py --checkpoint classified

# Resume from matching (skip OCR & classification)
python analyse_delta_i_for_one_AR.py --checkpoint matched

# Resume from evaluation (skip all except final analysis)
python analyse_delta_i_for_one_AR.py --checkpoint evaluated
```

## 💾 Caching System

The pipeline implements **5-layer intelligent caching** to avoid redundant processing and API calls:

| Stage | Cache Location | Benefit |
|-------|---------------|---------|
| **OCR** | `Decomposition_AR/ocr_content/[PDF]/` | Skip PDF processing (~30s) |
| **Classification** | `Decomposition_AR/output/classified_sentences/[PDF]/` | Skip LLM classification calls |
| **KB Matching** | `RAG_and_knowledgebase/output/[PDF]/` | Skip vector DB queries |
| **Evaluation** | `Evaluation/output/[PDF]/` | Skip LLM evaluation calls (~$0.50) |
| **KB Storage** | `RAG_and_knowledgebase/kb_storage/` | Reuse indexed company documents |

**Performance Impact:**
- **First run**: ~3-5 minutes (includes OCR, LLM calls, KB building)

**Cache Management:**

```bash
# Clear cache for a specific document
rm -rf */output/02_01_2023_Rosenblatt/
rm -rf Decomposition_AR/ocr_content/02_01_2023_Rosenblatt/

# Clear all caches (force fresh analysis)
rm -rf */output/*/
rm -rf Decomposition_AR/ocr_content/*/

# Rebuild knowledge base
rm -rf RAG_and_knowledgebase/kb_storage/
```

## 📊 Output Files

All outputs are organized by document name in stage-specific directories:

### Final Reports (`Analysis/output/[PDF_NAME]/`)
- **`analysis_report.txt`**: Human-readable comprehensive report
- **`statistics.json`**: Detailed statistics and metrics
- **`coverage_summary.json`**: Coverage percentages and breakdowns
- **`metadata.json`**: Analysis timestamp and info

### Example Output

```
Total Sentences: 151
Covered: 42 (27.8%)          ← Supported by company documents
Not Covered: 107 (70.9%)     ← Novel analyst insights! (ΔI)
Contradicted: 2 (1.3%)       ← Contradicts company statements
```

**Interpretation:**
- 70.9% of analyst claims are NOT found in company documents = **high information delta**
- These are potential novel insights that analysts are contributing

## ⚙️ Configuration Options

### settings.config

```ini
env_file=.env
analyst_report=data/AMD_2022_Q4/analyst_report/report.pdf
company_data_dir=data/AMD_2022_Q4/company_reports
```

### config.py (Advanced)

You can modify `config.py` to adjust:
- **Models**: `classification_model`, `evaluation_model`, `embedding_model`
- **Batch sizes**: `classification_batch_size`
- **Retrieval**: `top_k_results`, `chunk_size`
- **DS-RAG**: `use_semantic_sectioning`

## 🔬 Technical Details

### Models Used

- **Classification**: GPT-4o-mini (categorizes sentences)
- **Evaluation**: GPT-4o-mini (assesses evidence support)
- **Embeddings**: OpenAI text-embedding-3-small (via DS-RAG)
- **Reranking**: Cohere Rerank (optional, improves retrieval)

### DS-RAG Integration

The pipeline uses [DS-RAG](https://github.com/D-Star-AI/dsRAG) for advanced RAG capabilities:
- **Content-Driven Chunking**: Intelligent document segmentation
- **AutoContext**: LLM-generated context for each chunk
- **Semantic Search**: Vector similarity + keyword matching
- **Reranking**: Optional Cohere reranking for better results

### Evaluation Labels

| Label | Description |
|-------|-------------|
| **Supported** | Evidence fully backs the claim |
| **Partially Supported** | Evidence partially backs the claim |
| **Not Supported** | No supporting evidence found |
| **Contradicted** | Evidence directly contradicts the claim |
| **No Evidence** | No relevant evidence in knowledge base |

## 🐛 Troubleshooting

### Common Issues

**1. CUDA Compatibility Error**
```python
# The pipeline automatically forces CPU for OCR
# No action needed - it's handled internally
```

**2. API Key Errors**
```bash
# Check your .env file
cat .env

# Ensure keys are set
echo $OPENAI_API_KEY
```

**3. Out of Memory**
```python
# Reduce batch size in config.py
classification_batch_size = 5  # Default: 10
```

**4. Cohere Rate Limits**
```
# Cohere trial keys have limits
# Either upgrade to production key or disable reranking
# Reranking is optional - pipeline works without it
```

## 📚 Key Dependencies

- **docling** >= 1.0.0 - PDF OCR and text extraction
- **dsrag** - Advanced RAG framework
- **openai** - LLM classification and evaluation
- **cohere** (optional) - Reranking for better retrieval
- **pydantic** - Data validation and models

## 🤝 Contributing

This is an internal research pipeline. For questions or issues, contact the DataNXT team.

## 📄 License

Internal use only - Goethe University Research

---

## 🎯 Example Workflow

```bash
# 1. Setup
cd Analysis_Pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp env_template.txt .env
# Edit .env with your API keys
# Edit settings.config with your data paths

# 3. Run
python analyse_delta_i_for_one_AR.py

# 4. Review results
cat Analysis/output/02_01_2023_Rosenblatt/analysis_report.txt
```

## 📈 Performance Benchmarks

**Test Case**: AMD Q4 2022 Analyst Report
- Document: 8 pages, 151 sentences
- Company KB: 6 documents (10-Qs, 10-K, earnings call, presentation)

| Stage | First Run | Cached Run | API Calls |
|-------|-----------|------------|-----------|
| OCR | 30s | 0.01s | 0 |
| Classification | 45s | 0.01s | 15 → 0 |
| KB Matching | 60s | 0.01s | 151 → 0 |
| Evaluation | 90s | 0.01s | 151 → 0 |
| Analysis | 0.5s | 0.5s | 0 |
| **TOTAL** | **~3.5 min** | **~0.2s** | **317 → 0** |

**Cost Savings**: ~$0.75 per cached run

---

**Built with ❤️ by the Manú Weissel**

