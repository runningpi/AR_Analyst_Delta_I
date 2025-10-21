"""
Configuration file for SEC Filings Downloader
Customize these settings for your specific needs
"""

# SEC API Configuration
SEC_CONFIG = {
    "user_name": "Max Althaus",
    "user_email": "max.althaus@example.com",  # Replace with your actual email
    "rate_limit": True,  # Enable rate limiting to be respectful to SEC servers
    "delay_between_requests": 0.1  # Seconds to wait between requests
}

# Company Configuration
COMPANY_CONFIG = {
    "cik": "0000002488",  # AMD's Central Index Key
    "company_name": "AMD",
    "ticker": "AMD",
    "full_name": "Advanced Micro Devices, Inc."
}

# Download Configuration
DOWNLOAD_CONFIG = {
    "form_types": ["10-K", "10-Q", "8-K"],  # All form types
    "start_year": 2013,  # Full date range
    "end_year": 2023,
    "download_details": True,  # Download full submission details
    "include_amendments": False,  # Include amended filings
    "max_retries": 3,  # Maximum number of retry attempts for failed downloads
    "retry_delay": 5  # Seconds to wait between retry attempts
}

# Output Configuration
OUTPUT_CONFIG = {
    "base_output_dir": "../00_data/AMD/company_reports",
    "raw_filings_dir": "raw_filings",
    "renamed_filings_dir": "renamed_filings",
    "clean_content_dir": "clean_content",
    "create_date_folders": False,  # Create year-based subfolders
    "preserve_original_structure": True,  # Keep original SEC folder structure
    "overwrite_existing": False  # Whether to overwrite existing files
}

# Content Processing Configuration
PROCESSING_CONFIG = {
    "extract_tables": True,
    "extract_headers": True,
    "extract_lists": True,
    "min_text_length": 10,  # Minimum length for text to be included
    "remove_html_artifacts": True,
    "normalize_whitespace": True,
    "preserve_table_structure": True,  # Keep table formatting
    "extract_metadata": True  # Extract filing metadata
}

# File Naming Configuration
NAMING_CONFIG = {
    "use_standard_convention": True,  # Use the existing naming convention
    "include_filing_date": True,  # Include filing date in filename
    "include_quarter_info": True,  # Include quarter information for 10-Q filings
    "file_extension": ".html",  # Extension for renamed files
    "clean_text_extension": ".txt"  # Extension for clean text files
}

# Logging Configuration
LOGGING_CONFIG = {
    "log_level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    "log_to_file": True,
    "log_file": "sec_download.log",
    "log_format": "%(asctime)s - %(levelname)s - %(message)s",
    "max_log_size": 10 * 1024 * 1024,  # 10MB max log file size
    "backup_count": 5  # Number of backup log files to keep
}

# Error Handling Configuration
ERROR_CONFIG = {
    "continue_on_error": True,  # Continue processing if individual files fail
    "log_errors": True,  # Log all errors to file
    "retry_failed_downloads": True,  # Retry failed downloads
    "skip_corrupted_files": True  # Skip files that can't be processed
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    "batch_size": 10,  # Number of files to process in each batch
    "max_concurrent_downloads": 3,  # Maximum concurrent downloads
    "memory_limit_mb": 512,  # Memory limit for processing
    "temp_dir": None  # Temporary directory for processing (None = system default)
}

# Validation Configuration
VALIDATION_CONFIG = {
    "validate_downloads": True,  # Validate downloaded files
    "check_file_sizes": True,  # Check that files are not empty
    "verify_content": True,  # Verify that content was extracted properly
    "min_file_size_bytes": 1000  # Minimum expected file size
}

# Additional Company Configurations (for future use)
ADDITIONAL_COMPANIES = {
    "NVDA": {
        "cik": "0001045810",
        "company_name": "NVIDIA",
        "ticker": "NVDA",
        "full_name": "NVIDIA Corporation"
    },
    "INTC": {
        "cik": "0000050863",
        "company_name": "Intel",
        "ticker": "INTC",
        "full_name": "Intel Corporation"
    },
    "AAPL": {
        "cik": "0000320193",
        "company_name": "Apple",
        "ticker": "AAPL",
        "full_name": "Apple Inc."
    }
}

# Form Type Descriptions
FORM_TYPE_DESCRIPTIONS = {
    "10-K": "Annual Report - Comprehensive overview of company's business and financial condition",
    "10-Q": "Quarterly Report - Quarterly financial results and business updates",
    "8-K": "Current Report - Material events or corporate changes",
    "DEF 14A": "Proxy Statement - Information about annual meetings and voting",
    "S-1": "Registration Statement - Initial public offering or new securities",
    "S-3": "Registration Statement - Shelf registration for securities"
}

# Default Settings for Quick Start
DEFAULT_SETTINGS = {
    "company": "AMD",
    "years": [2013, 2023],
    "forms": ["10-K", "10-Q", "8-K"],
    "output_format": "both"  # "raw", "renamed", "clean", or "both"
}
