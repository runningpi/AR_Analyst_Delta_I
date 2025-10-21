#!/usr/bin/env python3
"""
Comprehensive SEC Filings Downloader and Content Processor
Downloads SEC filings and processes them into clean text format
Combines all functionality from the previous separate scripts into one unified solution

Features:
- Downloads SEC filings (10-K, 10-Q, 8-K) using SEC EDGAR API
- Extracts clean text content from HTML filings
- Handles file naming conventions and organization
- Provides comprehensive logging and error handling
- Configurable for different companies and date ranges
"""

import os
import re
import logging
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json

try:
    from sec_edgar_downloader import Downloader
    from bs4 import BeautifulSoup
    import requests
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    exit(1)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sec_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class SECFilingsDownloader:
    """
    Comprehensive SEC filings downloader and content processor
    Handles downloading, processing, and organizing SEC filings
    """
    
    def __init__(self, 
                 user_name: str = "Max Althaus",
                 user_email: str = "max.althaus@example.com",
                 company_cik: str = "0000002488",
                 company_name: str = "AMD",
                 base_output_dir: str = "../00_data/AMD/company_reports"):
        """
        Initialize the SEC filings downloader
        
        Args:
            user_name: Name for SEC API requests
            user_email: Email for SEC API requests
            company_cik: Company's Central Index Key
            company_name: Company name for file naming
            base_output_dir: Base directory for output files
        """
        self.user_name = user_name
        self.user_email = user_email
        self.company_cik = company_cik
        self.company_name = company_name
        self.base_output_dir = Path(base_output_dir)
        
        # Create output directories - form type folders directly in company_reports
        self.base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create form type directories directly
        self.form_dirs = {}
        for form_type in ["10-K", "10-Q", "8-K"]:
            form_dir = self.base_output_dir / form_type
            form_dir.mkdir(exist_ok=True)
            self.form_dirs[form_type] = form_dir
        
        # Temporary directory for processing (will be cleaned up)
        self.temp_dir = self.base_output_dir / "temp_processing"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize downloader with a more robust approach
        try:
            self.downloader = Downloader(
                user_name, 
                user_email, 
                download_folder=str(self.temp_dir)
            )
        except Exception as e:
            logger.warning(f"Failed to initialize sec-edgar-downloader: {e}")
            logger.info("Falling back to direct API approach...")
            self.downloader = None
        
        # Rate limiting
        self.request_delay = 0.1  # 100ms between requests
        
        # Direct API headers for fallback
        self.headers = {
            'User-Agent': f"{user_name} {user_email}",
            'Accept-Encoding': 'gzip, deflate'
        }
        
        logger.info(f"SEC Filings Downloader initialized for {company_name}")
        logger.info(f"CIK: {company_cik}")
        logger.info(f"Output directory: {self.base_output_dir}")
        logger.info(f"Form directories: {list(self.form_dirs.keys())}")
        logger.info(f"Temp processing: {self.temp_dir}")
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common HTML artifacts
        html_entities = {
            '&nbsp;': ' ',
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&#8217;': "'",
            '&#160;': ' ',
            '&apos;': "'",
            '&hellip;': '...',
            '&mdash;': '—',
            '&ndash;': '–'
        }
        
        for entity, replacement in html_entities.items():
            text = text.replace(entity, replacement)
        
        return text.strip()
    
    def clean_text_for_encoding(self, text: str) -> str:
        """Clean text to ensure it can be encoded as UTF-8."""
        if not text:
            return ""
        
        # Replace problematic characters that might cause encoding issues
        # Common problematic characters from SEC filings
        replacements = {
            '\u2018': "'",  # Left single quotation mark
            '\u2019': "'",  # Right single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '--', # Em dash
            '\u2026': '...', # Horizontal ellipsis
            '\u00a0': ' ',  # Non-breaking space
            '\u00ad': '',   # Soft hyphen
            '\u00ae': '(R)', # Registered trademark symbol
            '\u00a9': '(C)', # Copyright symbol
            '\u2122': '(TM)', # Trademark symbol
        }
        
        # Apply replacements
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Remove any remaining non-printable characters except newlines and tabs
        text = ''.join(char for char in text if char.isprintable() or char in '\n\t')
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        return text
    
    def remove_binary_attachments(self, content: str) -> str:
        """
        Remove binary attachments and embedded files from SEC filing content
        
        Args:
            content: Raw content from SEC filing
            
        Returns:
            Content with binary attachments removed
        """
        # Remove uuencoded content (starts with "begin" and ends with "end")
        # This pattern matches the corrupted data we saw
        content = re.sub(r'begin \d+ .*?end\s*', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove base64 encoded content that might be embedded
        # Look for long sequences of base64 characters (but be more conservative)
        content = re.sub(r'[A-Za-z0-9+/]{200,}={0,2}', '', content)
        
        # Remove XML/HTML document sections that contain binary data
        # Look for <DOCUMENT> sections with binary content
        content = re.sub(r'<DOCUMENT>.*?<TYPE>EXCEL.*?</DOCUMENT>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<DOCUMENT>.*?<TYPE>ZIP.*?</DOCUMENT>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<DOCUMENT>.*?<TYPE>PDF.*?</DOCUMENT>', '', content, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any remaining binary-like patterns
        # Look for sequences of non-printable characters or unusual patterns
        content = re.sub(r'[^\x20-\x7E\s]{20,}', '', content)
        
        # Remove patterns that look like corrupted binary data - be more specific
        # Only remove if we find the exact patterns we know are problematic
        binary_patterns = [
            r'[A-Z]\^\(\.I\d+.*',  # Pattern like "XE^(.I222" and everything after
            r'[A-Z]\$[A-Z0-9_]+.*',  # Pattern like "MX5$.,CZD$_C7%" and everything after
        ]
        
        for pattern in binary_patterns:
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # Remove excessive whitespace that might be left after removing binary content
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        return content.strip()
    
    def extract_text_directly(self, file_path: Path) -> str:
        """
        Extract text directly from a file without HTML parsing
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Keep all content as-is, including binary parts
            
            # Clean the content
            content = self.clean_text_for_encoding(content)
            
            # If the content is still very short, it might be mostly HTML tags
            # Try to extract just the text content
            if len(content.strip()) < 100:
                # Remove HTML tags and extract text
                import re
                # Remove HTML tags
                content = re.sub(r'<[^>]+>', ' ', content)
                # Clean up whitespace
                content = re.sub(r'\s+', ' ', content).strip()
            
            return content
            
        except Exception as e:
            logger.error(f"Error in direct text extraction from {file_path}: {e}")
            return ""
    
    def contains_binary_content(self, content: str) -> bool:
        """
        Check if content contains binary data that should be removed
        
        Args:
            content: Text content to check
            
        Returns:
            True if binary content is detected
        """
        # Check for uuencoded content
        if re.search(r'begin \d+ .*?end\s*', content, flags=re.DOTALL | re.IGNORECASE):
            return True
        
        # Check for long base64 sequences (be more conservative)
        if re.search(r'[A-Za-z0-9+/]{200,}={0,2}', content):
            return True
        
        # Check for XML/HTML document sections with binary content
        if re.search(r'<DOCUMENT>.*?<TYPE>(EXCEL|ZIP|PDF).*?</DOCUMENT>', content, flags=re.DOTALL | re.IGNORECASE):
            return True
        
        # Check for sequences of non-printable characters (be more conservative)
        if re.search(r'[^\x20-\x7E\s]{20,}', content):
            return True
        
        # Check for patterns that look like corrupted binary data
        # Look for sequences of characters that are typical of binary corruption
        binary_patterns = [
            r'[A-Z]\^\(\.I\d+',  # Pattern like "XE^(.I222" from the corrupted file
            r'[A-Z]\$[A-Z0-9_]+',  # Pattern like "MX5$.,CZD$_C7%"
        ]
        
        for pattern in binary_patterns:
            if re.search(pattern, content):
                return True
        
        return False
    
    def extract_table_content(self, table) -> str:
        """
        Extract content from HTML tables in a readable format
        
        Args:
            table: BeautifulSoup table element
            
        Returns:
            Formatted table content as text
        """
        if not table:
            return ""
        
        table_content = []
        
        # Process each row
        for row in table.find_all('tr'):
            row_cells = []
            
            # Process each cell
            for cell in row.find_all(['td', 'th']):
                cell_text = self.clean_text(cell.get_text())
                if cell_text:
                    row_cells.append(cell_text)
            
            if row_cells:
                # Join cells with tab separator for better readability
                table_content.append('\t'.join(row_cells))
        
        return '\n'.join(table_content)
    
    def get_company_submissions(self) -> Optional[Dict]:
        """Get all submissions for the company using direct SEC API"""
        url = f"https://data.sec.gov/submissions/CIK{self.company_cik}.json"
        
        try:
            logger.info(f"Fetching submissions from: {url}")
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            time.sleep(self.request_delay)
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching submissions: {e}")
            return None
    
    def get_filing_url(self, accession_number: str) -> str:
        """Convert accession number to filing URL"""
        # Remove dashes from accession number
        clean_accession = accession_number.replace('-', '')
        # Remove leading zeros from CIK for URL
        cik_for_url = str(int(self.company_cik))
        return f"https://www.sec.gov/Archives/edgar/data/{cik_for_url}/{clean_accession}/{accession_number}.txt"
    
    def download_and_process_filing_direct(self, filing_url: str, accession_number: str, form_type: str, filing_date: str) -> bool:
        """Download and immediately process a single filing using direct API"""
        try:
            logger.info(f"Downloading and processing: {form_type} from {filing_date}")
            response = requests.get(filing_url, headers=self.headers)
            response.raise_for_status()
            time.sleep(self.request_delay)
            
            # Create temporary file for processing
            temp_file = self.temp_dir / f"temp_{accession_number}.txt"
            with open(temp_file, 'wb') as f:
                f.write(response.content)
            
            # Extract clean content directly
            clean_content = self.extract_document_content(temp_file)
            
            # If content is empty, try to extract text directly from the raw content
            if not clean_content or len(clean_content.strip()) < 100:
                logger.warning(f"HTML parsing resulted in empty content for {accession_number}, trying direct text extraction")
                clean_content = self.extract_text_directly(temp_file)
            
            # Create clean filename
            clean_filename = self.create_standard_filename(form_type, filing_date)
            
            # Save clean content directly to form type directory with robust encoding handling
            clean_file = self.form_dirs[form_type] / clean_filename
            try:
                with open(clean_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(clean_content)
                logger.info(f"Successfully saved {clean_filename} with UTF-8 encoding")
            except UnicodeEncodeError as e:
                logger.warning(f"Unicode encoding error for {clean_filename}: {e}")
                # Fallback: clean the content and try again
                clean_content = self.clean_text_for_encoding(clean_content)
                with open(clean_file, 'w', encoding='utf-8', errors='replace') as f:
                    f.write(clean_content)
                logger.info(f"Successfully saved {clean_filename} after encoding cleanup")
            
            # Clean up temp file
            temp_file.unlink()
            
            logger.info(f"Successfully processed: {clean_filename}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading {form_type} from {filing_date}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error processing {form_type} from {filing_date}: {e}")
            return False
    
    def extract_filing_date(self, file_path: Path) -> Optional[str]:
        """
        Extract filing date from SEC submission file
        
        Args:
            file_path: Path to the full-submission.txt file
            
        Returns:
            Filing date in YYYY-MM-DD format, or None if not found
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Look for FILED AS OF DATE pattern
            date_match = re.search(r'FILED AS OF DATE:\s*(\d{8})', content)
            if date_match:
                date_str = date_match.group(1)
                # Convert YYYYMMDD to YYYY-MM-DD
                year = date_str[:4]
                month = date_str[4:6]
                day = date_str[6:8]
                return f"{year}-{month}-{day}"
                
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            
        return None
    
    def get_quarter_from_date(self, date_str: str) -> str:
        """
        Get quarter string from date
        
        Args:
            date_str: Date in YYYY-MM-DD format
            
        Returns:
            Quarter string like "Q1", "Q2", "Q3", "Q4"
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            month = date_obj.month
            
            if month <= 3:
                return "Q1"
            elif month <= 6:
                return "Q2"
            elif month <= 9:
                return "Q3"
            else:
                return "Q4"
        except:
            return "Q?"
    
    def create_standard_filename(self, form_type: str, filing_date: str) -> str:
        """
        Create standardized filename with correct naming convention
        
        Args:
            form_type: Type of filing (10-K, 10-Q, 8-K)
            filing_date: Filing date in YYYY-MM-DD format
            
        Returns:
            Standardized filename with correct naming
        """
        try:
            date_obj = datetime.strptime(filing_date, '%Y-%m-%d')
            year = date_obj.year
            month = date_obj.month
            
            # Create filename based on corrected convention
            if form_type == "10-K":
                # 10-K reports are for the previous year (filed in following year)
                # e.g., 10-K filed in 2023 reports on 2022
                report_year = year - 1
                return f"{report_year} {form_type}.txt"
                
            elif form_type == "10-Q":
                # 10-Q quarters are shifted - filing month determines previous quarter
                # e.g., May filing = Q1 report (Jan-Mar), not Q2
                if month <= 3:
                    # Filed in Q1, reports on previous year Q4
                    report_year = year - 1
                    quarter = "4Q"
                elif month <= 6:
                    # Filed in Q2, reports on Q1
                    report_year = year
                    quarter = "1Q"
                elif month <= 9:
                    # Filed in Q3, reports on Q2
                    report_year = year
                    quarter = "2Q"
                else:
                    # Filed in Q4, reports on Q3
                    report_year = year
                    quarter = "3Q"
                
                return f"{quarter}{report_year} {form_type}.txt"
                
            elif form_type == "8-K":
                # 8-K reports use exact filing date
                return f"{filing_date.replace('-', '_')} {form_type}.txt"
            else:
                return f"{filing_date.replace('-', '_')} {form_type}.txt"
                
        except Exception as e:
            logger.error(f"Error creating filename for {form_type} on {filing_date}: {e}")
            return f"{filing_date.replace('-', '_')} {form_type}.txt"
    
    def extract_document_content(self, html_file: Path) -> str:
        """
        Extract clean content from an HTML file, filtering out binary attachments
        
        Args:
            html_file: Path to the HTML file
            
        Returns:
            Clean document content
        """
        try:
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Keep all content as-is, including any binary attachments
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            document_content = []
            
            # Extract title
            title = soup.find('title')
            if title:
                document_content.append(f"TITLE: {self.clean_text(title.get_text())}")
                document_content.append("=" * 80)
                document_content.append("")
            
            # Extract headers (h1, h2, h3, etc.)
            for header in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                header_text = self.clean_text(header.get_text())
                if header_text:
                    level = header.name[1]  # Get the number from h1, h2, etc.
                    document_content.append(f"{'#' * int(level)} {header_text}")
                    document_content.append("")
            
            # Extract tables
            tables = soup.find_all('table')
            if tables:
                document_content.append("TABLES:")
                document_content.append("-" * 40)
                for i, table in enumerate(tables, 1):
                    table_content = self.extract_table_content(table)
                    if table_content:
                        document_content.append(f"Table {i}:")
                        document_content.append(table_content)
                        document_content.append("")
            
            # Extract paragraphs and other text content
            for element in soup.find_all(['p', 'div', 'span', 'td', 'th']):
                # Skip if it's inside a table (already processed)
                if element.find_parent('table'):
                    continue
                
                text = self.clean_text(element.get_text())
                if text and len(text) > 10:  # Only include substantial text
                    # Check if it looks like a meaningful paragraph
                    if not re.match(r'^[^\w]*$', text):  # Not just punctuation
                        # Check if this text is the same as the last line to avoid duplication
                        if not document_content or document_content[-1] != text:
                            document_content.append(text)
                            document_content.append("")
            
            # Extract lists
            for list_elem in soup.find_all(['ul', 'ol']):
                # Skip if it's inside a table (already processed)
                if list_elem.find_parent('table'):
                    continue
                
                list_items = []
                for item in list_elem.find_all('li'):
                    item_text = self.clean_text(item.get_text())
                    if item_text:
                        list_items.append(f"• {item_text}")
                
                if list_items:
                    document_content.append("LIST:")
                    document_content.extend(list_items)
                    document_content.append("")
            
            return '\n'.join(document_content)
            
        except Exception as e:
            logger.error(f"Error processing {html_file}: {e}")
            return f"Error processing file: {e}"
    
    def download_filings(self, 
                        form_types: List[str] = ["10-K", "10-Q", "8-K"],
                        start_year: int = 2022,
                        end_year: int = 2023) -> Dict[str, int]:
        """
        Download SEC filings for the company
        
        Args:
            form_types: List of form types to download
            start_year: Start year for downloads
            end_year: End year for downloads
            
        Returns:
            Dictionary with counts of downloaded files by form type
        """
        logger.info(f"Starting SEC filings download for {self.company_name} ({start_year}-{end_year})")
        logger.info(f"Form types: {form_types}")
        
        download_counts = {"10-K": 0, "10-Q": 0, "8-K": 0}
        
        logger.info("Using direct SEC API approach for immediate processing...")
        # Use direct API approach
        submissions = self.get_company_submissions()
        if not submissions:
            logger.error("Failed to get company submissions")
            return download_counts
        
        # Filter filings by date and form type
        start_date = f"{start_year}-01-01"
        end_date = f"{end_year}-12-31"
        
        filings = submissions.get('filings', {}).get('recent', {})
        accession_numbers = filings.get('accessionNumber', [])
        filing_dates = filings.get('filingDate', [])
        form_types_list = filings.get('form', [])
        
        logger.info(f"Found {len(accession_numbers)} total filings, filtering for {form_types} from {start_date} to {end_date}")
        
        for i, (accession, date, form_type) in enumerate(zip(accession_numbers, filing_dates, form_types_list)):
            # Check if filing is in our target date range and form types
            if (start_date <= date <= end_date and 
                form_type in form_types):
                
                # Download and process the filing directly
                filing_url = self.get_filing_url(accession)
                if self.download_and_process_filing_direct(filing_url, accession, form_type, date):
                    download_counts[form_type] += 1
        
        # Fix any encoding issues in the downloaded files
        logger.info("Checking for encoding issues in downloaded files...")
        self.fix_encoding_issues()
        
        return download_counts
    
    def fix_encoding_issues(self) -> None:
        """Fix encoding issues and remove binary content from all downloaded .txt files."""
        logger.info("Checking and fixing encoding issues in downloaded files...")
        
        fixed_count = 0
        error_count = 0
        
        for form_type in ["10-K", "10-Q", "8-K"]:
            form_dir = self.form_dirs[form_type]
            if not form_dir.exists():
                continue
                
            txt_files = list(form_dir.glob("*.txt"))
            logger.info(f"Checking {len(txt_files)} {form_type} files for encoding issues...")
            
            for txt_file in txt_files:
                try:
                    # Try to read the file to detect encoding issues
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # File is already UTF-8, no changes needed
                    
                except UnicodeDecodeError:
                    # File has encoding issues, fix it
                    logger.info(f"Fixing encoding issues in {txt_file.name}")
                    
                    try:
                        # Create backup
                        backup_path = txt_file.with_suffix(txt_file.suffix + '.backup')
                        with open(txt_file, 'rb') as src, open(backup_path, 'wb') as dst:
                            dst.write(src.read())
                        
                        # Try to read with different encodings
                        content = None
                        for encoding in ['cp1252', 'latin-1', 'iso-8859-1']:
                            try:
                                with open(txt_file, 'r', encoding=encoding, errors='replace') as f:
                                    content = f.read()
                                logger.info(f"Successfully read {txt_file.name} with {encoding} encoding")
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if content is None:
                            logger.error(f"Could not read {txt_file.name} with any encoding")
                            error_count += 1
                            continue
                        
                        # Keep all content as-is
                        
                        # Clean the content for encoding issues
                        content = self.clean_text_for_encoding(content)
                        
                        # Write back as UTF-8
                        with open(txt_file, 'w', encoding='utf-8', errors='replace') as f:
                            f.write(content)
                        
                        # Remove backup if successful
                        backup_path.unlink()
                        
                        fixed_count += 1
                        logger.info(f"Successfully fixed encoding for {txt_file.name}")
                        
                    except Exception as e:
                        logger.error(f"Error fixing encoding for {txt_file.name}: {e}")
                        error_count += 1
        
        logger.info(f"Encoding fix complete: {fixed_count} files fixed, {error_count} errors")
    
    def cleanup_temp_files(self) -> None:
        """Clean up temporary processing files"""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info("Cleaned up temporary processing files")
        except Exception as e:
            logger.warning(f"Could not clean up temp files: {e}")
    
    def get_processed_counts(self) -> Dict[str, int]:
        """
        Get counts of already processed clean text files
        
        Returns:
            Dictionary with counts of processed files by form type
        """
        processed_counts = {"10-K": 0, "10-Q": 0, "8-K": 0}
        
        for form_type in ["10-K", "10-Q", "8-K"]:
            form_dir = self.form_dirs[form_type]
            if form_dir.exists():
                processed_counts[form_type] = len(list(form_dir.glob("*.txt")))
        
        return processed_counts
    
    def create_comprehensive_summary(self, download_counts: Dict[str, int]) -> None:
        """
        Create a comprehensive summary of all operations
        
        Args:
            download_counts: Count of downloaded and processed files by form type
        """
        summary_file = self.base_output_dir / "COMPREHENSIVE_SUMMARY.txt"
        
        with open(summary_file, 'w') as f:
            f.write("SEC Filings Download and Processing Summary\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Processing Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Company: {self.company_name} (CIK: {self.company_cik})\n")
            f.write(f"User: {self.user_name} ({self.user_email})\n\n")
            
            f.write("Download and Processing Results:\n")
            f.write("-" * 30 + "\n")
            for form_type, count in download_counts.items():
                f.write(f"{form_type}: {count} clean text files created\n")
            
            f.write(f"\nTotal Summary:\n")
            f.write(f"  Processed: {sum(download_counts.values())} clean text files\n")
            
            f.write(f"\nOutput Directory:\n")
            f.write(f"  Company reports: {self.base_output_dir}\n")
            
            # List files in each directory
            f.write(f"\nFile Structure:\n")
            for form_type in ["10-K", "10-Q", "8-K"]:
                form_dir = self.form_dirs[form_type]
                if form_dir.exists():
                    files = list(form_dir.glob("*.txt"))
                    f.write(f"\n{form_type} Clean Text Files ({len(files)} files):\n")
                    files.sort()
                    for file in files:
                        f.write(f"  - {file.name}\n")
        
        logger.info(f"Comprehensive summary created: {summary_file}")
    
    def run_complete_pipeline(self, 
                             form_types: List[str] = ["10-K", "10-Q", "8-K"],
                             start_year: int = 2013,
                             end_year: int = 2023) -> Dict[str, int]:
        """
        Run the complete SEC filings download and processing pipeline
        
        Args:
            form_types: List of form types to download
            start_year: Start year for downloads
            end_year: End year for downloads
            
        Returns:
            Dictionary with processed file counts
        """
        logger.info("=" * 80)
        logger.info("STARTING COMPLETE SEC FILINGS DOWNLOAD AND PROCESSING PIPELINE")
        logger.info("=" * 80)
        
        # Step 1: Download and process filings directly
        logger.info("STEP 1: Downloading and processing SEC filings directly to clean text...")
        processed_counts = self.download_filings(form_types, start_year, end_year)
        
        # Step 2: Clean up temporary files
        logger.info("STEP 2: Cleaning up temporary files...")
        self.cleanup_temp_files()
        
        # Step 3: Create comprehensive summary
        logger.info("STEP 3: Creating comprehensive summary...")
        self.create_comprehensive_summary(processed_counts)
        
        logger.info("=" * 80)
        logger.info("SEC FILINGS DOWNLOAD AND PROCESSING PIPELINE COMPLETE")
        logger.info("=" * 80)
        
        return processed_counts


def main():
    """Main function to run the SEC filings download and processing"""
    
    # Configuration - Update these values as needed
    USER_NAME = "Max Althaus"
    USER_EMAIL = "max.althaus@example.com"  # Replace with your actual email
    COMPANY_CIK = "0000002488"  # AMD's CIK
    COMPANY_NAME = "AMD"
    OUTPUT_DIR = "../00_data/AMD/company_reports"
    
    # Initialize downloader
    downloader = SECFilingsDownloader(
        user_name=USER_NAME,
        user_email=USER_EMAIL,
        company_cik=COMPANY_CIK,
        company_name=COMPANY_NAME,
        base_output_dir=OUTPUT_DIR
    )
    
    # Run complete pipeline
    try:
        results = downloader.run_complete_pipeline(
            form_types=["10-K", "10-Q", "8-K"],
            start_year=2013,
            end_year=2023
        )
        
        # Print results
        print("\n" + "=" * 80)
        print("SEC FILINGS DOWNLOAD AND PROCESSING RESULTS")
        print("=" * 80)
        
        print("\nProcessed Files:")
        for form_type, count in results.items():
            print(f"  {form_type}: {count} clean text files")
        
        total_processed = sum(results.values())
        
        print(f"\nTotal Summary:")
        print(f"  Processed: {total_processed} clean text files")
        
        print(f"\nOutput Directory:")
        print(f"  Company reports: {downloader.base_output_dir}")
        
        print("\n" + "=" * 80)
        print("SUCCESS: SEC filings download and processing completed!")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Error in main pipeline: {e}")
        print(f"\nERROR: {e}")
        print("Please check the configuration and try again.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
