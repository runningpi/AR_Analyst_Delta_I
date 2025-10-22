#!/usr/bin/env python3
"""
Test script for the improved SEC downloader.
Downloads a small sample of filings to verify functionality.
"""

import json
import logging
from pathlib import Path
from amd_sec_downloader import download_and_convert

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_download():
    """Test the download functionality with a small sample."""
    logger.info("Testing SEC downloader with sample data...")
    
    # Test parameters - just 10-K for 2024
    cik = "0000002488"  # AMD
    forms = ["10-K"]  # Just 10-K forms
    start_year = 2024
    end_year = 2024
    output_dir = Path("test_filings")
    pause = 0.5  # Slower for testing
    
    logger.info(f"Testing with: {forms} for {start_year}")
    
    try:
        total = download_and_convert(
            cik=cik,
            forms=forms,
            start_y=start_year,
            end_y=end_year,
            outdir=output_dir,
            pause=pause
        )
        
        if total > 0:
            logger.info(f"Test successful! Downloaded {total} files to {output_dir}")
            
            # List downloaded files
            if output_dir.exists():
                files = list(output_dir.glob("*.md"))
                logger.info(f"Downloaded files:")
                for file in files:
                    logger.info(f"  - {file.name}")
        else:
            logger.warning("No files downloaded in test")
            
        return total > 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_download()
    if success:
        print("Test passed!")
    else:
        print("Test failed!")
