# AR Analyst Delta I Project

**Quantifying Novel Insights in Financial Analyst Reports**

This project analyzes analyst reports to calculate the **information delta (ΔI)** - the truly novel information that analysts provide beyond what's already disclosed in official company documents.

## 🎯 Project Formula

```
ΔI = ΔAR - ΔΣ

Where:
  ΔAR = Information in Analyst Reports
  ΔΣ  = Information in Company Documents (10-K, 10-Q, earnings calls, etc.)
  ΔI  = Information Delta (novel analyst insights)
```

## 📁 Project Structure

```
AR_Analyst_Delta_I/
│
├── 📊 Analysis_Pipeline/          # ⭐ Main Production Pipeline
│   │
│   │   Complete automated pipeline for analyzing analyst reports
│   │   against company documents using OCR, LLM classification,
│   │   RAG matching, and evaluation.
│   │
│   ├── 🎯 core/                   # Orchestration & data models
│   ├── 📂 Decomposition_AR/       # OCR & sentence classification
│   ├── 📂 RAG_and_knowledgebase/  # DS-RAG knowledge base & matching
│   ├── 📂 Evaluation/             # LLM-based evaluation
│   ├── 📂 Analysis/               # Reports & statistics
│   └── 📄 README.md               # Full pipeline documentation
│
├── 🧪 Playground/                 # Experimental & Development
│   ├── docling_ocr/               # Docling OCR experiments
│   ├── mistral_OCR/               # Mistral OCR experiments
│   └── GPT_information_extraction/ # LLM extraction prototypes
│
└── 📝 data/                       # Input datasets
    └── [COMPANY]/[QUARTER]/
        ├── analyst_report/        # Analyst reports (PDFs)
        └── company_reports/       # Company documents (PDFs)
```

## 🚀 Getting Started

### Quick Start

The **Analysis Pipeline** is the main production system. To get started:

```bash
# Navigate to the pipeline
cd Analysis_Pipeline/

# Follow the setup instructions
cat README.md
```

### What Does It Do?

The Analysis Pipeline:

1. **📄 Extracts** text from analyst report PDFs using Docling OCR
2. **🏷️ Classifies** sentences into categories (corporate info, market info, analyst interpretation)
3. **🔍 Matches** each sentence against a knowledge base of company documents using DS-RAG
4. **⚖️ Evaluates** whether sentences are Supported, Contradicted, or Novel using GPT-4
5. **📊 Generates** comprehensive reports with coverage statistics and insights

### Key Output

```
Coverage Analysis Example:
├── Supported:     42 (27.8%) ← Backed by company documents
├── Not Supported: 107 (70.9%) ← Novel analyst insights (ΔI) ⭐
└── Contradicted:  2 (1.3%)   ← Conflicts with official data
```

**High "Not Supported" percentage = High information delta = Novel insights!**

## 📚 Documentation

| Document | Description |
|----------|-------------|
| **[Analysis_Pipeline/README.md](Analysis_Pipeline/README.md)** | Complete pipeline documentation, installation, usage |
| **[Analysis_Pipeline/WORKFLOW_DIAGRAM.md](Analysis_Pipeline/WORKFLOW_DIAGRAM.md)** | Detailed technical workflow diagrams |
| **[Analysis_Pipeline/settings.config](Analysis_Pipeline/settings.config)** | Configuration file for data paths |

## 🛠️ Technical Stack

- **OCR**: Docling (PDF text extraction)
- **RAG**: DS-RAG (knowledge base & retrieval)
- **LLM**: GPT-4o-mini (classification & evaluation)
- **Embeddings**: OpenAI text-embedding-3-small
- **Reranking**: Cohere Rerank (optional)
- **Language**: Python 3.10+

## 📊 Use Cases

### Research Applications

1. **Analyst Alpha Measurement**: Quantify how much novel information analysts provide
2. **Information Quality**: Assess accuracy of analyst claims vs. company disclosures
3. **Coverage Gaps**: Identify areas where company disclosures are insufficient
4. **Contradiction Detection**: Find inconsistencies between analyst reports and official data

### Example Research Questions

- Do sell-side analysts provide novel information beyond company disclosures?
- What percentage of analyst claims are independently verifiable?
- Which analysts consistently provide the highest information delta?
- Are certain sections (e.g., risk factors) more novel than others?

## 🎓 Academic Context

This project supports research in:
- **Financial Information Economics**: Measuring information production by intermediaries
- **Market Efficiency**: Testing whether analysts add information to markets
- **Corporate Disclosure**: Identifying gaps in company communications
- **NLP for Finance**: Applying modern AI to financial text analysis

## 🏗️ Development Workflow

### Production Pipeline

```bash
cd Analysis_Pipeline/
python analyse_delta_i_for_one_AR.py
```

### Experimentation

```bash
cd Playground/
# Explore different OCR methods, classification prompts, etc.
```

### Adding New Data

```bash
# Add company data
mkdir -p data/COMPANY_NAME/QUARTER/company_reports/
# Copy PDFs to company_reports/

# Add analyst report
mkdir -p data/COMPANY_NAME/QUARTER/analyst_report/
# Copy PDF to analyst_report/

# Update Analysis_Pipeline/settings.config
# Then run pipeline
```

## 🔧 Configuration

Edit `Analysis_Pipeline/settings.config`:

```ini
env_file=.env
analyst_report=data/COMPANY/QUARTER/analyst_report/report.pdf
company_data_dir=data/COMPANY/QUARTER/company_reports
```

## 📈 Performance

- **First Run**: ~3-5 minutes (includes OCR, LLM calls, KB indexing)
- **Cached Runs**: ~0.2 seconds (loads cached results)
- **Cost**: ~$0.50-1.00 per analyst report (OpenAI API)

**Intelligent Caching**: All stages (OCR, classification, matching, evaluation) are cached to prevent redundant processing.

## 🤝 Contributing

### Project Maintainers
- **Manú Weissel** - Goethe University Research

### Development Guidelines
- Production code goes in `Analysis_Pipeline/`
- Experiments go in `Playground/`
- All outputs are cached in stage-specific subdirectories
- Follow the logging standards from DataNXT

## 📄 License

Internal use only - Goethe University Research

---

## 🎯 Next Steps

1. **Read the full documentation**: [Analysis_Pipeline/README.md](Analysis_Pipeline/README.md)
2. **Set up the environment**: Follow Quick Start guide
3. **Run your first analysis**: Process an analyst report
4. **Review the results**: Check the Analysis/output/ directory

## 📧 Contact

For questions about this project, contact the research team at Goethe University.

---

**Built with ❤️ for financial research at Goethe University**

