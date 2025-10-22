# SEC Filings Downloader - Improved Version

This directory contains an improved SEC filings downloader that replaces the previous complex implementation with a cleaner, more efficient approach.

## Files

- `amd_sec_downloader.py` - Core downloader script based on the improved logic
- `run_sec_download.py` - Pipeline integration wrapper
- `test_download.py` - Test script for verification
- `config.json` - Configuration file for download settings
- `requirements.txt` - Updated dependencies including pandas

## Key Improvements

1. **Simplified Logic**: Direct approach to fetch SEC filings without complex intermediate steps
2. **Better HTML Processing**: Uses BeautifulSoup with lxml for more reliable HTML parsing
3. **Markdown Output**: Converts HTML directly to clean Markdown format instead of complex text extraction
4. **Table Extraction**: Uses pandas to properly extract and format tables
5. **Better Error Handling**: More robust error handling and logging
6. **Rate Limiting**: Proper rate limiting to respect SEC API guidelines
7. **Cleaner Code**: Much more maintainable and readable codebase

## Usage

### Command Line

```bash
# Download 10-Q and 10-K filings for 2022-2024
python amd_sec_downloader.py --forms 10-Q 10-K --start 2022 --end 2024

# Download only 10-K filings for 2024
python amd_sec_downloader.py --forms 10-K --start 2024 --end 2024

# Use custom output directory
python amd_sec_downloader.py --forms 10-Q 10-K --start 2022 --end 2024 --outdir my_filings
```

### Pipeline Integration

```python
from run_sec_download import run_sec_download_pipeline

# Run with default config
total_files = run_sec_download_pipeline()

# Run with custom config
total_files = run_sec_download_pipeline("custom_config.json")
```

### Testing

```bash
# Run test download (downloads 1 10-K filing from 2024)
python test_download.py
```

## Configuration

The `config.json` file contains:

```json
{
  "company": {
    "cik": "0000002488",
    "name": "Advanced Micro Devices Inc",
    "user_agent": "AMD Research Tool contact@example.com"
  },
  "download_settings": {
    "form_types": ["10-Q", "10-K"],
    "start_year": 2022,
    "end_year": 2024,
    "rate_limit_seconds": 0.25
  },
  "output_settings": {
    "markdown_files_dir": "filings_markdown"
  }
}
```

## Dependencies

- requests>=2.28.0
- beautifulsoup4>=4.11.0
- lxml>=4.9.0
- pandas>=1.5.0

## Output

The downloader creates Markdown files with:
- Clean, readable text content
- Properly formatted tables
- Structured sections (title, tables, text)
- Removed XBRL and technical elements

## Integration with Main Pipeline

The main pipeline (`analyse_delta_i_for_one_AR.py`) has been updated to use this improved downloader. It will:

1. Create a temporary config file from the main pipeline settings
2. Call the new downloader to fetch SEC filings
3. Save the Markdown files to the company data directory
4. Continue with the rest of the analysis pipeline

## Migration from Old Downloader

The old `amd_8k_complete_pipeline.py` has been replaced. The new system:

- Is much simpler and more reliable
- Produces cleaner output (Markdown instead of complex text files)
- Has better error handling
- Is easier to maintain and extend
- Integrates seamlessly with the existing pipeline
