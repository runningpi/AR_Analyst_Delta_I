# SEC Filings Downloader

A comprehensive Python tool for downloading and processing SEC filings from the EDGAR database. This unified script combines all the functionality from the previous separate scripts into one powerful, easy-to-use solution.

## Features

- **Download SEC Filings**: Downloads 10-K, 10-Q, and 8-K filings using the official SEC EDGAR API
- **Content Extraction**: Extracts clean text content from HTML filings, removing formatting while preserving structure
- **File Organization**: Organizes files with standardized naming conventions
- **Comprehensive Logging**: Detailed logging of all operations with error handling
- **Configurable**: Easy configuration through a dedicated config file
- **Multiple Output Formats**: Provides raw files, renamed files, and clean text files

## Quick Start

### 1. Installation

```bash
# Install required packages
pip install -r requirements.txt
```

### 2. Configuration

Edit `config.py` to customize your settings:

```python
# Update your contact information (required by SEC)
SEC_CONFIG = {
    "user_name": "Your Name",
    "user_email": "your.email@example.com",  # Replace with your actual email
}

# Configure company and date range
COMPANY_CONFIG = {
    "cik": "0000002488",  # AMD's CIK
    "company_name": "AMD",
    "ticker": "AMD"
}

DOWNLOAD_CONFIG = {
    "form_types": ["10-K", "10-Q", "8-K"],
    "start_year": 2013,
    "end_year": 2023
}
```

### 3. Run the Downloader

```bash
# Simple run with configuration
python run_downloader.py

# Or run the main script directly
python sec_filings_downloader.py
```

## File Structure

After running the downloader, you'll have the following structure:

```
00_data/AMD/company_reports/
├── raw_filings/                    # Original downloaded files
│   └── sec-edgar-filings/
│       └── 0000002488/
│           ├── 10-K/
│           ├── 10-Q/
│           └── 8-K/
├── renamed_filings/                # Files with standardized names
│   ├── 10-K/
│   ├── 10-Q/
│   └── 8-K/
├── clean_content/                  # Clean text files ready for analysis
│   ├── 10-K/
│   ├── 10-Q/
│   ├── 8-K/
│   └── COMPREHENSIVE_SUMMARY.txt
└── sec_download.log               # Detailed log file
```

## Configuration Options

### SEC API Configuration
- `user_name`: Your name for SEC API requests
- `user_email`: Your email address (required by SEC)
- `rate_limit`: Enable rate limiting to be respectful to SEC servers
- `delay_between_requests`: Delay between API requests

### Company Configuration
- `cik`: Company's Central Index Key
- `company_name`: Company name for file naming
- `ticker`: Stock ticker symbol

### Download Configuration
- `form_types`: Types of filings to download (10-K, 10-Q, 8-K, etc.)
- `start_year` / `end_year`: Date range for downloads
- `include_amendments`: Whether to include amended filings
- `max_retries`: Maximum retry attempts for failed downloads

### Output Configuration
- `base_output_dir`: Base directory for all output files
- `overwrite_existing`: Whether to overwrite existing files
- `preserve_original_structure`: Keep original SEC folder structure

### Content Processing Configuration
- `extract_tables`: Extract and format tables
- `extract_headers`: Extract document headers
- `extract_lists`: Extract bulleted and numbered lists
- `min_text_length`: Minimum length for text to be included
- `remove_html_artifacts`: Clean HTML entities and formatting

## File Naming Conventions

The downloader uses standardized naming conventions:

- **10-K filings**: `YYYY 10-K.html` (e.g., `2023 10-K.html`)
- **10-Q filings**: `QXYYYY 10-Q.html` (e.g., `1Q2023 10-Q.html`)
- **8-K filings**: `YYYY QX - 8-K.html` (e.g., `2023 Q1 - 8-K.html`)

Clean text files use the same naming with `.txt` extension.

## Usage Examples

### Basic Usage
```python
from sec_filings_downloader import SECFilingsDownloader

# Initialize downloader
downloader = SECFilingsDownloader(
    user_name="Your Name",
    user_email="your.email@example.com",
    company_cik="0000002488",
    company_name="AMD"
)

# Run complete pipeline
results = downloader.run_complete_pipeline(
    form_types=["10-K", "10-Q", "8-K"],
    start_year=2013,
    end_year=2023
)
```

### Custom Configuration
```python
# Download only 10-K filings for a specific year range
results = downloader.run_complete_pipeline(
    form_types=["10-K"],
    start_year=2020,
    end_year=2023
)
```

### Individual Steps
```python
# Download only
download_counts = downloader.download_filings(["10-K", "10-Q"], 2020, 2023)

# Rename and organize
renamed_counts = downloader.rename_and_organize_filings()

# Process to clean text
processed_counts = downloader.process_filings_to_clean_text()
```

## Supported Companies

The configuration includes several popular companies:

- **AMD** (Advanced Micro Devices): CIK 0000002488
- **NVIDIA**: CIK 0001045810
- **Intel**: CIK 0000050863
- **Apple**: CIK 0000320193

To use a different company, update the `COMPANY_CONFIG` in `config.py`.

## Form Types

Supported SEC form types:

- **10-K**: Annual Report - Comprehensive business and financial overview
- **10-Q**: Quarterly Report - Quarterly financial results
- **8-K**: Current Report - Material events or corporate changes
- **DEF 14A**: Proxy Statement - Annual meeting and voting information
- **S-1**: Registration Statement - IPO or new securities
- **S-3**: Registration Statement - Shelf registration

## Error Handling

The downloader includes comprehensive error handling:

- **Retry Logic**: Automatically retries failed downloads
- **Continue on Error**: Continues processing even if individual files fail
- **Detailed Logging**: Logs all operations and errors
- **Validation**: Validates downloaded files and content

## Logging

All operations are logged to `sec_download.log` with detailed information:

- Download progress and results
- File processing status
- Error messages and troubleshooting information
- Performance metrics

## Troubleshooting

### Common Issues

1. **Permission Errors**
   - Ensure you have write permissions to the output directory
   - Check that the directory exists and is accessible

2. **Network Errors**
   - Verify your internet connection
   - Check SEC server status
   - Try again after a few minutes if rate limited

3. **Missing Files**
   - Some filings might not be available for certain periods
   - Check the log file for specific error messages
   - Verify the company CIK is correct

4. **Import Errors**
   - Install all required packages: `pip install -r requirements.txt`
   - Ensure you're using Python 3.7 or higher

### Getting Help

1. Check the log file (`sec_download.log`) for detailed error information
2. Verify your configuration in `config.py`
3. Ensure your email address is correct (required by SEC)
4. Check that you have the required Python packages installed

## Legal Notice

This tool is for educational and research purposes. Please ensure compliance with SEC terms of service and any applicable laws when downloading and using SEC filings.

## Requirements

- Python 3.7+
- Internet connection
- Valid email address for SEC API compliance

## Dependencies

See `requirements.txt` for the complete list of required packages. Key dependencies:

- `sec-edgar-downloader`: SEC EDGAR API access
- `beautifulsoup4`: HTML parsing and content extraction
- `requests`: HTTP requests
- `pandas`: Data processing (optional)

## License

This project is provided as-is for educational and research purposes.

