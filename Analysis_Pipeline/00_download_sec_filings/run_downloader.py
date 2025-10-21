#!/usr/bin/env python3
"""
Simple runner script for the SEC Filings Downloader
Uses configuration from config.py for easy customization
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import configuration and downloader
from config import (
    SEC_CONFIG, COMPANY_CONFIG, DOWNLOAD_CONFIG, 
    OUTPUT_CONFIG, PROCESSING_CONFIG, NAMING_CONFIG
)
from sec_filings_downloader import SECFilingsDownloader


def main():
    """Main function to run SEC filings download with configuration"""
    
    print("=" * 80)
    print("SEC FILINGS DOWNLOADER")
    print("=" * 80)
    print(f"Company: {COMPANY_CONFIG['full_name']} ({COMPANY_CONFIG['ticker']})")
    print(f"CIK: {COMPANY_CONFIG['cik']}")
    print(f"User: {SEC_CONFIG['user_name']} ({SEC_CONFIG['user_email']})")
    print(f"Period: {DOWNLOAD_CONFIG['start_year']}-{DOWNLOAD_CONFIG['end_year']}")
    print(f"Form Types: {', '.join(DOWNLOAD_CONFIG['form_types'])}")
    print(f"Output Directory: {OUTPUT_CONFIG['base_output_dir']}")
    print("=" * 80)
    
    # Initialize downloader with configuration
    downloader = SECFilingsDownloader(
        user_name=SEC_CONFIG['user_name'],
        user_email=SEC_CONFIG['user_email'],
        company_cik=COMPANY_CONFIG['cik'],
        company_name=COMPANY_CONFIG['company_name'],
        base_output_dir=OUTPUT_CONFIG['base_output_dir']
    )
    
    # Run complete download and processing pipeline
    try:
        results = downloader.run_complete_pipeline(
            form_types=DOWNLOAD_CONFIG['form_types'],
            start_year=DOWNLOAD_CONFIG['start_year'],
            end_year=DOWNLOAD_CONFIG['end_year']
        )
        
        # Print detailed results
        print("\n" + "=" * 80)
        print("DOWNLOAD AND PROCESSING RESULTS")
        print("=" * 80)
        
        print("\nProcessed Files:")
        total_processed = 0
        for form_type, count in results.items():
            print(f"  {form_type}: {count} clean text files")
            total_processed += count
        
        print(f"\nTotal Summary:")
        print(f"  Processed: {total_processed} clean text files")
        
        print(f"\nOutput Directory:")
        print(f"  Company reports: {downloader.base_output_dir}")
        
        print("\n" + "=" * 80)
        print("SUCCESS: SEC filings download and processing completed!")
        print("=" * 80)
        
        # Show next steps
        print("\nNext Steps:")
        print("1. Check the clean content files in the clean_content directory")
        print("2. Review the comprehensive summary for detailed information")
        print("3. Use the clean text files for your analysis pipeline")
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {e}")
        print("Please check the configuration and try again.")
        print("\nTroubleshooting:")
        print("1. Verify your internet connection")
        print("2. Check that your email address is correct in config.py")
        print("3. Ensure you have write permissions to the output directory")
        print("4. Check the log file for detailed error information")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
