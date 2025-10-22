"""
Main pipeline orchestrator for AR Analyst Delta I analysis.

This module orchestrates the complete pipeline:
1. Text extraction and parsing
2. Sentence classification
3. Knowledge base setup
4. RAG query and matching
5. LLM evaluation
6. Analysis and reporting
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from config import PipelineConfig

# Import using dynamic imports to handle numbered folder names
decomp_ocr = __import__('01_Decomposition_AR.ocr_docling_utils', fromlist=['DoclingParser'])
DoclingParser = decomp_ocr.DoclingParser

decomp_text = __import__('01_Decomposition_AR.text_mangement_utils', fromlist=['TextManager', 'ClassificationManager', 'EvaluationManager'])
TextManager = decomp_text.TextManager
ClassificationManager = decomp_text.ClassificationManager
EvaluationManager = decomp_text.EvaluationManager

decomp_class = __import__('01_Decomposition_AR.classification_service', fromlist=['ClassificationService'])
ClassificationService = decomp_class.ClassificationService

rag_utils = __import__('02_RAG_and_knowledgebase.DS_RAG_utils', fromlist=['KnowledgeBaseManager'])
KnowledgeBaseManager = rag_utils.KnowledgeBaseManager

rag_matching = __import__('02_RAG_and_knowledgebase.matching_utils', fromlist=['SentenceMatcher'])
SentenceMatcher = rag_matching.SentenceMatcher

eval_utils = __import__('03_Evaluation.evaluation_utils', fromlist=['EvaluationService'])
EvaluationService = eval_utils.EvaluationService

from .analysis import EvaluationAnalyzer, ReportGenerator

logger = logging.getLogger(__name__)


class ARAnalysisPipeline:
    """Main pipeline for analyzing analyst reports against company documents."""
    
    def __init__(self, config: PipelineConfig):
        """
        Initialize the pipeline with configuration.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config
        
        # Initialize components
        self.docling_parser = DoclingParser()
        self.text_manager = TextManager()
        self.classification_service = None
        self.kb_manager = None
        self.sentence_matcher = None
        self.evaluation_service = None
        
        logger.info("ARAnalysisPipeline initialized")
    
    def setup_classification_service(self) -> None:
        """Initialize the classification service."""
        self.classification_service = ClassificationService(
            model=self.config.classification_model,
            batch_size=self.config.classification_batch_size,
        )
        logger.info("Classification service initialized")
    
    def setup_knowledge_base(self, kb_id: str) -> None:
        """
        Initialize and populate the knowledge base.
        
        Args:
            kb_id: Knowledge base identifier
        """
        logger.info(f"Setting up knowledge base: {kb_id}")
        
        # Initialize KB manager
        self.kb_manager = KnowledgeBaseManager(
            kb_id=kb_id,
            storage_directory=self.config.kb_storage_dir,
            llm_model=self.config.embedding_model,
            use_reranker=True,
            chunk_size=self.config.chunk_size,
            use_semantic_sectioning=self.config.use_semantic_sectioning,
        )
        
        # Add company documents (both PDF and TXT files)
        doc_ids = self.kb_manager.add_documents_from_directory(
            directory=self.config.company_data_dir,
            file_pattern="*.txt",  # DS-RAG utils only supports single pattern
        )
        
        logger.info(f"Knowledge base populated with {len(doc_ids)} documents")
    
    def setup_matching_service(self) -> None:
        """Initialize the sentence matching service."""
        if not self.kb_manager:
            raise RuntimeError("Knowledge base must be initialized first")
        
        self.sentence_matcher = SentenceMatcher(
            kb_manager=self.kb_manager,
            top_k=self.config.top_k_results,
        )
        logger.info("Matching service initialized")
    
    def setup_evaluation_service(self) -> None:
        """Initialize the evaluation service."""
        self.evaluation_service = EvaluationService(
            model=self.config.evaluation_model,
        )
        logger.info("Evaluation service initialized")
    
    def extract_and_parse_text(
        self,
        text_dict: Dict[str, str]
    ) -> Dict[str, List[str]]:
        """
        Extract and parse text into sentences.
        
        Args:
            text_dict: Dictionary mapping section names to section text
            
        Returns:
            Dictionary mapping section names to sentence lists
        """
        logger.info("Extracting and parsing text into sentences")
        
        sections = self.docling_parser.parse_sections_from_text(text_dict)
        
        # Note: Extracted sections are saved to Decomposition_AR/ocr_content/[PDF_NAME]/
        # when using PDF extraction. No separate save needed here for text_dict input.
        
        return sections
    
    def classify_sentences(
        self,
        sections: Dict[str, List[str]],
        pdf_name: str = None,
        use_cached: bool = True
    ) -> Dict[str, List[Dict[str, str]]]:
        """
        Classify all sentences in sections.
        
        Args:
            sections: Dictionary mapping section names to sentence lists
            pdf_name: Name of the PDF (for caching), defaults to analyst report name
            use_cached: Whether to use cached classification if available
            
        Returns:
            Dictionary mapping section names to lists of classified sentence dicts
        """
        import json
        from datetime import datetime
        from pathlib import Path
        
        logger.info("Classifying sentences")
        
        # Determine PDF name for caching
        if pdf_name is None:
            pdf_name = self.config.analyst_report_path.stem
        
        # Setup classification cache directory
        classification_cache_dir = Path(__file__).parent.parent / "01_Decomposition_AR" / "output" / "classified_sentences"
        doc_cache_dir = classification_cache_dir / pdf_name
        cache_file = doc_cache_dir / "classified_sentences.json"
        
        # Check if cached classification exists
        if use_cached and cache_file.exists():
            logger.info(f"✓ Found cached classified sentences at: {cache_file}")
            logger.info("Loading classifications from cache (skipping classification)...")
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    classified = json.load(f)
                
                total_sentences = sum(len(items) for items in classified.values())
                logger.info(f"✓ Loaded classifications for {total_sentences} sentences from cache")
                
                # Load and display metadata if available
                metadata_path = doc_cache_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    logger.info(f"  Originally classified: {metadata.get('classified_at', 'unknown')}")
                
                return classified
                
            except Exception as e:
                logger.warning(f"Failed to load cached classifications: {e}")
                logger.info("Falling back to fresh classification...")
        
        # No cached output or use_cached=False: proceed with fresh classification
        if use_cached:
            logger.info("No cached classifications found. Running classification...")
        else:
            logger.info("Cached classifications disabled. Running classification...")
        
        if not self.classification_service:
            self.setup_classification_service()
        
        classified = self.classification_service.classify_sentences(sections)
        
        # Save to cache directory
        doc_cache_dir.mkdir(parents=True, exist_ok=True)
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(classified, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved classified sentences to cache: {cache_file}")
        
        # Save metadata
        total_sentences = sum(len(items) for items in classified.values())
        source_counts = {}
        for items in classified.values():
            for item in items:
                source = item.get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1
        
        metadata = {
            "pdf_file": str(self.config.analyst_report_path),
            "pdf_filename": self.config.analyst_report_path.name,
            "classified_at": datetime.now().isoformat(),
            "total_sections": len(classified),
            "total_sentences": total_sentences,
            "source_distribution": source_counts,
            "model_used": self.config.classification_model,
            "batch_size": self.config.classification_batch_size
        }
        
        metadata_path = doc_cache_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved classification metadata: {metadata_path}")
        
        return classified
    
    def match_sentences(
        self,
        classified_sentences: Dict[str, List[Dict[str, str]]],
        pdf_name: str = None,
        use_cached: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Match sentences against knowledge base.
        
        Args:
            classified_sentences: Dictionary of classified sentences
            pdf_name: Name of the PDF being processed (for caching)
            use_cached: Whether to use cached query results if available
            
        Returns:
            Dictionary mapping sections to query results with evidence
        """
        import json
        from datetime import datetime
        
        logger.info("Matching sentences against knowledge base")
        
        # Determine PDF name
        if pdf_name is None:
            pdf_name = self.config.analyst_report_path.stem
        
        # Setup cache directory
        rag_cache_dir = Path(__file__).parent.parent / "02_RAG_and_knowledgebase" / "output"
        doc_cache_dir = rag_cache_dir / pdf_name
        cache_file = doc_cache_dir / "query_results.json"
        
        # Check cache
        if use_cached and cache_file.exists():
            logger.info(f"✓ Found cached query results at: {cache_file}")
            logger.info("Loading query results from cache (skipping matching)...")
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    query_results = json.load(f)
                
                total_sentences = sum(len(items) for items in query_results.values())
                logger.info(f"✓ Loaded query results for {total_sentences} sentences from cache")
                
                metadata_path = doc_cache_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    logger.info(f"  Originally matched: {metadata.get('matched_at', 'unknown')}")
                
                return query_results
                
            except Exception as e:
                logger.warning(f"Failed to load cached query results: {e}")
                logger.info("Falling back to fresh matching...")
        
        if use_cached:
            logger.info("No cached query results found. Running matching...")
        else:
            logger.info("Cached query results disabled. Running matching...")
        
        # Setup matcher
        if not self.sentence_matcher:
            self.setup_matching_service()
        
        # Perform matching
        query_results = self.sentence_matcher.match_classified_sentences(
            classified_sentences,
            show_progress=True,
        )
        
        # Save to cache directory
        doc_cache_dir.mkdir(parents=True, exist_ok=True)
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(query_results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved query results to cache: {cache_file}")
        
        # Save metadata
        total_sentences = sum(len(items) for items in query_results.values())
        evidence_counts = {}
        for section_items in query_results.values():
            for item in section_items:
                evidence_count = len(item.get('evidence', []))
                evidence_counts[evidence_count] = evidence_counts.get(evidence_count, 0) + 1
        
        metadata = {
            "pdf_file": str(self.config.analyst_report_path),
            "pdf_filename": self.config.analyst_report_path.name,
            "matched_at": datetime.now().isoformat(),
            "total_sections": len(query_results),
            "total_sentences": total_sentences,
            "evidence_distribution": evidence_counts,
            "kb_id": self.kb_manager.kb_id if self.kb_manager else "unknown"
        }
        
        metadata_path = doc_cache_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved query metadata: {metadata_path}")
        
        return query_results
    
    def evaluate_sentences(
        self,
        query_results: Dict[str, List[Dict[str, Any]]],
        pdf_name: str = None,
        use_cached: bool = True
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Evaluate sentences using LLM.
        
        Args:
            query_results: Dictionary of query results with evidence
            pdf_name: Name of the PDF being processed (for caching)
            use_cached: Whether to use cached evaluation results if available
            
        Returns:
            Dictionary mapping sections to evaluations
        """
        import json
        from datetime import datetime
        
        logger.info("Evaluating sentences with LLM")
        
        # Determine PDF name
        if pdf_name is None:
            pdf_name = self.config.analyst_report_path.stem
        
        # Setup cache directory
        evaluation_cache_dir = Path(__file__).parent.parent / "03_Evaluation" / "output"
        doc_cache_dir = evaluation_cache_dir / pdf_name
        cache_file = doc_cache_dir / "evaluations.json"
        
        # Check cache
        if use_cached and cache_file.exists():
            logger.info(f"✓ Found cached evaluation results at: {cache_file}")
            logger.info("Loading evaluations from cache (skipping LLM evaluation)...")
            
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    evaluations_dict = json.load(f)
                
                total_sentences = sum(len(items) for items in evaluations_dict.values())
                logger.info(f"✓ Loaded evaluations for {total_sentences} sentences from cache")
                
                metadata_path = doc_cache_dir / "metadata.json"
                if metadata_path.exists():
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    logger.info(f"  Originally evaluated: {metadata.get('evaluated_at', 'unknown')}")
                
                return evaluations_dict
                
            except Exception as e:
                logger.warning(f"Failed to load cached evaluations: {e}")
                logger.info("Falling back to fresh evaluation...")
        
        if use_cached:
            logger.info("No cached evaluations found. Running LLM evaluation...")
        else:
            logger.info("Cached evaluations disabled. Running LLM evaluation...")
        
        # Setup evaluation service
        if not self.evaluation_service:
            self.setup_evaluation_service()
        
        # Perform evaluation
        evaluations = self.evaluation_service.evaluate_query_results(
            query_results,
            show_progress=True,
        )
        
        # Convert to dict for JSON serialization
        evaluations_dict = self.evaluation_service.evaluations_to_dict(evaluations)
        
        # Save to cache directory
        doc_cache_dir.mkdir(parents=True, exist_ok=True)
        
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(evaluations_dict, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved evaluations to cache: {cache_file}")
        
        # Calculate statistics
        total_sentences = sum(len(items) for items in evaluations_dict.values())
        evaluation_counts = {}
        for section_items in evaluations_dict.values():
            for item in section_items:
                eval_label = item.get('evaluation', 'Unknown')
                evaluation_counts[eval_label] = evaluation_counts.get(eval_label, 0) + 1
        
        # Save metadata
        metadata = {
            "pdf_file": str(self.config.analyst_report_path),
            "pdf_filename": self.config.analyst_report_path.name,
            "evaluated_at": datetime.now().isoformat(),
            "total_sections": len(evaluations_dict),
            "total_sentences": total_sentences,
            "evaluation_distribution": evaluation_counts,
            "model_used": self.config.evaluation_model
        }
        
        metadata_path = doc_cache_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved evaluation metadata: {metadata_path}")
        
        return evaluations_dict
    
    def analyze_and_report(
        self,
        evaluations: Dict[str, List[Dict[str, Any]]],
        pdf_name: str = None
    ) -> EvaluationAnalyzer:
        """
        Analyze evaluation results and generate reports.
        
        Args:
            evaluations: Dictionary of evaluation results
            pdf_name: Name of the PDF being processed (for organized output)
            
        Returns:
            EvaluationAnalyzer instance
        """
        import json
        from datetime import datetime
        
        logger.info("Analyzing evaluation results")
        
        # Determine PDF name
        if pdf_name is None:
            pdf_name = self.config.analyst_report_path.stem
        
        # Setup analysis output directory
        analysis_output_dir = Path(__file__).parent.parent / "04_Analysis" / "output"
        doc_output_dir = analysis_output_dir / pdf_name
        doc_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create analyzer
        analyzer = EvaluationAnalyzer(evaluations)
        
        # Generate and save report
        report_generator = ReportGenerator(analyzer)
        report_path = doc_output_dir / "analysis_report.txt"
        report_generator.save_report(str(report_path))
        logger.info(f"Saved analysis report: {report_path}")
        
        # Save detailed statistics
        stats = analyzer.get_overall_stats()
        stats_path = doc_output_dir / "statistics.json"
        self.text_manager.save_json(stats, stats_path)
        logger.info(f"Saved statistics: {stats_path}")
        
        # Save coverage summary
        coverage = analyzer.get_coverage_summary()
        coverage_path = doc_output_dir / "coverage_summary.json"
        self.text_manager.save_json(coverage, coverage_path)
        logger.info(f"Saved coverage summary: {coverage_path}")
        
        # Save metadata
        metadata = {
            "pdf_file": str(self.config.analyst_report_path),
            "pdf_filename": self.config.analyst_report_path.name,
            "analyzed_at": datetime.now().isoformat(),
            "total_sections": len(evaluations),
            "total_sentences": sum(len(items) for items in evaluations.values())
        }
        
        metadata_path = doc_output_dir / "metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved analysis metadata: {metadata_path}")
        
        logger.info(f"Analysis and reporting complete. All outputs saved to: {doc_output_dir}")
        return analyzer
    
    def run_full_pipeline(
        self,
        text_dict: Optional[Dict[str, str]] = None,
        kb_id: str = "analyst_report_kb",
        extract_from_pdf: bool = True,
    ) -> EvaluationAnalyzer:
        """
        Run the complete analysis pipeline.
        
        Args:
            text_dict: Optional dictionary mapping section names to section text.
                      If None and extract_from_pdf=True, will extract from PDF in config.
            kb_id: Knowledge base identifier
            extract_from_pdf: If True, extract text from PDF using Docling
            
        Returns:
            EvaluationAnalyzer with results
        """
        logger.info("=" * 80)
        logger.info("Starting full AR Analysis Pipeline")
        logger.info("=" * 80)
        
        try:
            # Step 1: Extract and parse text
            logger.info("STEP 1: Extract and parse text")
            
            if text_dict is not None:
                # Use provided text dictionary
                sections = self.extract_and_parse_text(text_dict)
            elif extract_from_pdf:
                # Extract directly from PDF using Docling
                logger.info(f"Extracting text from PDF: {self.config.analyst_report_path}")
                
                # Define OCR output directory
                from pathlib import Path
                # Note: pipeline.py is now in 00_core/, so go up one level to reach 01_Decomposition_AR
                ocr_output_dir = Path(__file__).parent.parent / "01_Decomposition_AR" / "ocr_content"
                
                sections = self.docling_parser.parse_pdf_to_sections(
                    self.config.analyst_report_path,
                    save_ocr_output=True,
                    ocr_output_base_dir=ocr_output_dir,
                    use_cached=True  # Use cached OCR if available
                )
            else:
                raise ValueError(
                    "Either text_dict must be provided or extract_from_pdf must be True"
                )
            
            # Step 2: Classify sentences
            logger.info("STEP 2: Classify sentences")
            pdf_name = self.config.analyst_report_path.stem
            classified = self.classify_sentences(sections, pdf_name=pdf_name, use_cached=True)
            
            # Step 3: Setup knowledge base
            logger.info("STEP 3: Setup knowledge base")
            self.setup_knowledge_base(kb_id)
            self.setup_matching_service()
            
            # Step 4: Match sentences
            logger.info("STEP 4: Match sentences against KB")
            query_results = self.match_sentences(classified, pdf_name=pdf_name, use_cached=True)
            
            # Step 5: Evaluate sentences
            logger.info("STEP 5: Evaluate sentences with LLM")
            evaluations = self.evaluate_sentences(query_results, pdf_name=pdf_name, use_cached=True)
            
            # Step 6: Analyze and report
            logger.info("STEP 6: Analyze and generate reports")
            analyzer = self.analyze_and_report(evaluations, pdf_name=pdf_name)
            
            logger.info("=" * 80)
            logger.info("Pipeline completed successfully!")
            logger.info("=" * 80)
            
            return analyzer
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            raise
    
    def run_from_checkpoint(
        self,
        checkpoint: str,
        **kwargs
    ) -> EvaluationAnalyzer:
        """
        Run pipeline from a specific checkpoint.
        
        Args:
            checkpoint: Checkpoint name (e.g., 'classified', 'matched', 'evaluated')
            **kwargs: Additional arguments for the checkpoint
            
        Returns:
            EvaluationAnalyzer with results
        """
        logger.info(f"Resuming pipeline from checkpoint: {checkpoint}")
        
        if checkpoint == "classified":
            # Load classified sentences from cache
            pdf_name = self.config.analyst_report_path.stem
            classification_cache_dir = Path(__file__).parent.parent / "01_Decomposition_AR" / "output" / "classified_sentences"
            classified_path = classification_cache_dir / pdf_name / "classified_sentences.json"
            
            with open(classified_path, 'r', encoding='utf-8') as f:
                import json
                classified = json.load(f)
            
            # Setup KB
            kb_id = kwargs.get("kb_id", "analyst_report_kb")
            self.setup_knowledge_base(kb_id)
            self.setup_matching_service()
            
            # Continue from matching
            query_results = self.match_sentences(classified, pdf_name=pdf_name, use_cached=True)
            evaluations = self.evaluate_sentences(query_results, pdf_name=pdf_name, use_cached=True)
            return self.analyze_and_report(evaluations, pdf_name=pdf_name)
        
        elif checkpoint == "matched":
            # Load query results from cache
            pdf_name = self.config.analyst_report_path.stem
            rag_cache_dir = Path(__file__).parent.parent / "02_RAG_and_knowledgebase" / "output"
            query_results_path = rag_cache_dir / pdf_name / "query_results.json"
            
            with open(query_results_path, 'r', encoding='utf-8') as f:
                import json
                query_results = json.load(f)
            
            # Continue from evaluation
            evaluations = self.evaluate_sentences(query_results, pdf_name=pdf_name, use_cached=True)
            return self.analyze_and_report(evaluations, pdf_name=pdf_name)
        
        elif checkpoint == "evaluated":
            # Load evaluations from cache
            pdf_name = self.config.analyst_report_path.stem
            evaluation_cache_dir = Path(__file__).parent.parent / "03_Evaluation" / "output"
            evaluations_path = evaluation_cache_dir / pdf_name / "evaluations.json"
            
            with open(evaluations_path, 'r', encoding='utf-8') as f:
                import json
                evaluations = json.load(f)
            
            return self.analyze_and_report(evaluations, pdf_name=pdf_name)
        
        else:
            raise ValueError(f"Unknown checkpoint: {checkpoint}")

