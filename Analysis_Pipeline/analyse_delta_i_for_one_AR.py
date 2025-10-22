"""
Entry point script for analyzing a single Analyst Report.

This script runs the complete AR Analyst Delta I pipeline to analyze
one analyst report against company documents.

Usage:
    python analyse_delta_i_for_one_AR.py [--config settings.config] [--checkpoint CHECKPOINT]
"""

import sys
import logging
from pathlib import Path
from typing import Optional

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from config import PipelineConfig

# Import pipeline using dynamic import to handle numbered folder names
core_pipeline = __import__('00_core.pipeline', fromlist=['ARAnalysisPipeline'])
ARAnalysisPipeline = core_pipeline.ARAnalysisPipeline

# Import SEC filings downloader
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent / "00_download_sec_filings"))
from run_sec_download import run_sec_download_pipeline


# Configure logging
def setup_logging(log_level: str = "INFO") -> None:
    """Setup logging configuration."""
    # Create logging directory if it doesn't exist
    log_dir = Path('05_logging')
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_dir / 'pipeline.log'),
        ]
    )


def download_sec_filings(config: PipelineConfig) -> None:
    """Download SEC filings if enabled in configuration."""
    logger = logging.getLogger(__name__)
    
    if not config.download_sec_filings:
        logger.info("SEC filings download is disabled in configuration")
        return
    
    logger.info("SEC filings download is enabled - starting download...")
    
    try:
        # Create a temporary config dict from the main settings
        import json
        import tempfile
        
        sec_config = {
            "company": {
                "cik": config.sec_company_cik,
                "name": config.sec_company_name,
                "user_agent": config.sec_user_agent
            },
            "download_settings": {
                "form_types": config.sec_form_types.split(','),
                "start_year": config.sec_start_year,
                "end_year": config.sec_end_year,
                "rate_limit_seconds": config.sec_rate_limit_seconds
            },
            "output_settings": {
                "markdown_files_dir": str(config.company_data_dir)
            }
        }
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_config:
            json.dump(sec_config, temp_config, indent=2)
            temp_config_path = temp_config.name
        
        # Debug logging
        logger.info(f"Created temporary config file: {temp_config_path}")
        logger.info(f"SEC config - Start year: {sec_config['download_settings']['start_year']}, End year: {sec_config['download_settings']['end_year']}")
        
        # Use the new improved downloader
        total_downloaded = run_sec_download_pipeline(temp_config_path)
        
        if total_downloaded > 0:
            logger.info(f"SEC filings download completed successfully")
            logger.info(f"Downloaded {total_downloaded} markdown files to: {config.company_data_dir}")
        else:
            logger.warning("No SEC filings were downloaded")
        
        # Clean up temporary config file
        import os
        os.unlink(temp_config_path)
        
    except Exception as e:
        logger.error(f"SEC filings download failed: {e}")
        logger.warning("Continuing with existing company data files...")


def main(
    config_path: str = "settings.config",
    checkpoint: Optional[str] = None,
    text_dict: Optional[dict] = None,
) -> None:
    """
    Main entry point for the pipeline.
    
    Args:
        config_path: Path to settings.config file
        checkpoint: Optional checkpoint to resume from
        text_dict: Optional pre-extracted text dictionary (for testing)
    """
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info(f"Loading configuration from: {config_path}")
        config = PipelineConfig.from_settings_file(config_path)
        config.validate()
        
        logger.info("Configuration loaded successfully")
        logger.info(f"\n{config}")
        
        # Download SEC filings if enabled
        download_sec_filings(config)
        
        # Initialize pipeline
        pipeline = ARAnalysisPipeline(config)
        
        # Run pipeline
        if checkpoint:
            # Resume from checkpoint
            logger.info(f"Resuming from checkpoint: {checkpoint}")
            analyzer = pipeline.run_from_checkpoint(checkpoint)
        else:
            # Run full pipeline
            if text_dict is None:
                # Extract from PDF using Docling
                logger.info("No text_dict provided. Extracting from PDF using Docling...")
                logger.info(f"Analyst report: {config.analyst_report_path}")
                
                try:
                    analyzer = pipeline.run_full_pipeline(
                        text_dict=None,
                        extract_from_pdf=True
                    )
                except Exception as e:
                    logger.error(f"PDF extraction failed: {e}")
                    
                    # Try to load from extracted_sentences.json if it exists
                    extracted_path = config.get_output_path("extracted_sentences.json")
                    if extracted_path.exists():
                        logger.info(f"Trying to load pre-extracted sentences from: {extracted_path}")
                        decomposition_module = __import__('01_Decomposition_AR.text_mangement_utils', fromlist=['TextManager'])
                        TextManager = decomposition_module.TextManager
                        text_manager = TextManager()
                        sections = text_manager.load_sections_from_json(extracted_path)
                        
                        # Continue from classification
                        pdf_name = config.analyst_report_path.stem
                        classified = pipeline.classify_sentences(sections, pdf_name=pdf_name, use_cached=True)
                        kb_id = "analyst_report_kb"
                        pipeline.setup_knowledge_base(kb_id)
                        pipeline.setup_matching_service()
                        query_results = pipeline.match_sentences(classified, pdf_name=pdf_name, use_cached=True)
                        evaluations = pipeline.evaluate_sentences(query_results, pdf_name=pdf_name, use_cached=True)
                        analyzer = pipeline.analyze_and_report(evaluations, pdf_name=pdf_name)
                    else:
                        logger.error("PDF extraction failed and no pre-extracted text found. Exiting.")
                        raise
            else:
                analyzer = pipeline.run_full_pipeline(text_dict)
        
        # Print summary
        print("\n" + "=" * 80)
        print("ANALYSIS COMPLETE!")
        print("=" * 80)
        
        coverage = analyzer.get_coverage_summary()
        print(f"\nTotal Sentences: {coverage['total_sentences']}")
        print(f"Covered: {coverage['covered']} ({coverage['covered_percentage']}%)")
        print(f"Not Covered: {coverage['not_covered']} ({coverage['not_covered_percentage']}%)")
        print(f"Contradicted: {coverage['contradicted']} ({coverage['contradicted_percentage']}%)")
        
        print(f"\nResults saved to stage-specific directories:")
        print(f"  - Analysis reports: 04_Analysis/output/{config.analyst_report_path.stem}/")
        print(f"  - Evaluations: 03_Evaluation/output/{config.analyst_report_path.stem}/")
        print(f"  - KB queries: 02_RAG_and_knowledgebase/output/{config.analyst_report_path.stem}/")
        print(f"  - Classifications: 01_Decomposition_AR/output/classified_sentences/{config.analyst_report_path.stem}/")
        print("=" * 80 + "\n")
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze Analyst Report against company documents"
    )
    parser.add_argument(
        "--config",
        default="settings.config",
        help="Path to settings.config file (default: settings.config)"
    )
    parser.add_argument(
        "--checkpoint",
        choices=["classified", "matched", "evaluated"],
        help="Resume from checkpoint (optional)"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Override log level if specified
    if args.log_level:
        setup_logging(args.log_level)
    
    main(
        config_path=args.config,
        checkpoint=args.checkpoint,
    )

