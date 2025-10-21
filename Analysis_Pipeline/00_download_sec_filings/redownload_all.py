#!/usr/bin/env python3
"""
Script to re-download all SEC filing files with original behavior (keeping all content including binary parts)
"""

import sys
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from sec_filings_downloader import SECFilingsDownloader

def redownload_all_files():
    """Re-download all SEC filing files with original behavior"""
    
    # Path to the company reports directory
    base_dir = Path("C:/Users/maalthau/eCommerce-Goethe Dropbox/Max Althaus/Projekte/AR_Analyst_Delta_I/Analysis_Pipeline/00_data/AMD/company_reports")
    
    # Initialize downloader
    downloader = SECFilingsDownloader(
        user_name="Re-download Script",
        user_email="redownload@example.com",
        company_cik="0000002488",
        company_name="AMD",
        base_output_dir=str(base_dir)
    )
    
    print("Re-downloading all SEC filing files with original behavior...")
    print("This will keep all content including any binary attachments.")
    
    # Download all form types for a reasonable date range
    results = downloader.download_filings(
        form_types=["10-K", "10-Q", "8-K"],
        start_year=2020,
        end_year=2023
    )
    
    print(f"Download results: {results}")
    print("Re-download complete!")
    print("All files now contain their original content including any binary attachments.")

if __name__ == "__main__":
    redownload_all_files()
