#!/usr/bin/env python3
"""
SEC Filings Download Pipeline Integration

This script integrates the improved SEC downloader with the analysis pipeline.
It downloads filings and saves them as Markdown files for further processing.
"""

import json
import logging
import sys
from pathlib import Path
from amd_sec_downloader import download_and_convert, CIK_DEFAULT

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Configuration file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        raise

def run_sec_download_pipeline(config_path: str = "config.json") -> int:
    """
    Run the SEC download pipeline using the improved downloader.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Number of files downloaded
    """
    try:
        # Load configuration
        config = load_config(config_path)
        
        # Extract settings - using fixed values for company info
        cik = "0000002488"  # Fixed AMD CIK
        company_name = "AMD"  # Fixed company name
        user_agent = "AMD Research Tool (research@example.com)"  # Fixed user agent
        rate_limit = 0.1  # Fixed rate limit
        
        # Get configurable settings from config or use defaults
        forms = config.get('download_settings', {}).get('form_types', ["10-Q", "10-K"])
        start_year = config.get('download_settings', {}).get('start_year', 2023)
        end_year = config.get('download_settings', {}).get('end_year', 2024)
        output_dir = config['output_settings']['markdown_files_dir']
        
        logger.info(f"Starting SEC download for {company_name} (CIK: {cik})")
        logger.info(f"Form types: {', '.join(forms)}")
        logger.info(f"Date range: {start_year}-{end_year}")
        logger.info(f"Output directory: {output_dir}")
        
        # Run the download
        total_downloaded = download_and_convert(
            cik=cik,
            forms=forms,
            start_y=start_year,
            end_y=end_year,
            outdir=Path(output_dir),
            pause=rate_limit
        )
        
        logger.info(f"Download completed successfully. Total files: {total_downloaded}")
        return total_downloaded
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 0

def main():
    """Main function for command line usage."""
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    else:
        config_path = "config.json"
    
    total_files = run_sec_download_pipeline(config_path)
    
    if total_files > 0:
        logger.info(f"SUCCESS: Downloaded {total_files} SEC filings")
        sys.exit(0)
    else:
        logger.error("FAILED: No files downloaded")
        sys.exit(1)

if __name__ == "__main__":
    main()
