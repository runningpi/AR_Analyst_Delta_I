#!/usr/bin/env python3
"""
AMD SEC Filings Complete Pipeline

This comprehensive script combines all functionality for downloading, extracting, and converting
AMD SEC filings (8-K, 10-Q, 10-K) from the SEC EDGAR API. It includes:

1. Downloading SEC filings for AMD with configurable form types and date ranges
2. Extracting content using BeautifulSoup
3. Converting to text files
4. Analysis and reporting

Author: AI Assistant
Date: 2024
"""

import os
import requests
import time
import json
import re
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
from bs4 import BeautifulSoup
from collections import Counter, defaultdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================================================
# PART 1: AMD SEC FILINGS DOWNLOADER
# ============================================================================

class AMDSECFilingsDownloader:
    def __init__(self, config_path: str = "config.json"):
        """
        Initialize the AMD SEC filings downloader.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config = self._load_config(config_path)
        
        self.cik = self.config['company']['cik']
        self.company_name = self.config['company']['name']
        self.form_types = self.config['download_settings']['form_types']
        self.start_year = self.config['download_settings']['start_year']
        self.end_year = self.config['download_settings']['end_year']
        self.rate_limit = self.config['download_settings']['rate_limit_seconds']
        
        # SEC EDGAR API endpoints
        self.base_url = "https://data.sec.gov"
        self.submissions_url = f"{self.base_url}/submissions/CIK{self.cik}.json"
        
        # Required headers for SEC API
        self.headers = {
            'User-Agent': self.config['company']['user_agent'],
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'data.sec.gov'
        }
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
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
    
    def _rate_limit(self, seconds: Optional[float] = None):
        """Add rate limiting to respect SEC API guidelines."""
        if seconds is None:
            seconds = self.rate_limit
        time.sleep(seconds)
    
    def get_company_submissions(self) -> Optional[Dict]:
        """
        Fetch company submissions data from SEC EDGAR API.
        
        Returns:
            Dictionary containing company submissions data or None if failed
        """
        try:
            logger.info(f"Fetching submissions data for {self.company_name} (CIK: {self.cik})")
            response = requests.get(self.submissions_url, headers=self.headers)
            response.raise_for_status()
            
            self._rate_limit()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch submissions data: {e}")
            return None
    
    def filter_filings_by_date_range(self, submissions_data: Dict) -> List[Dict]:
        """
        Filter filings by form types and date range.
        
        Args:
            submissions_data: Company submissions data from SEC API
            
        Returns:
            List of filing dictionaries matching criteria
        """
        filtered_filings = []
        
        if 'filings' not in submissions_data or 'recent' not in submissions_data['filings']:
            logger.error("Invalid submissions data structure")
            return filtered_filings
        
        recent_filings = submissions_data['filings']['recent']
        
        # Get the form types, filing dates, and accession numbers
        form_types = recent_filings.get('form', [])
        filing_dates = recent_filings.get('filingDate', [])
        accession_numbers = recent_filings.get('accessionNumber', [])
        
        logger.info(f"Processing {len(form_types)} recent filings...")
        
        for i, form_type in enumerate(form_types):
            if form_type in self.form_types and i < len(filing_dates) and i < len(accession_numbers):
                filing_date = filing_dates[i]
                
                # Check if filing is within the specified date range
                if self._is_date_in_range(filing_date):
                    filing_info = {
                        'form_type': form_type,
                        'filing_date': filing_date,
                        'accession_number': accession_numbers[i],
                        'index': i
                    }
                    filtered_filings.append(filing_info)
        
        logger.info(f"Found {len(filtered_filings)} filings for {self.start_year}-{self.end_year}")
        
        # Log breakdown by form type
        form_counts = {}
        for filing in filtered_filings:
            form_type = filing['form_type']
            form_counts[form_type] = form_counts.get(form_type, 0) + 1
        
        for form_type, count in form_counts.items():
            logger.info(f"  {form_type}: {count} filings")
        
        return filtered_filings
    
    def _is_date_in_range(self, filing_date: str) -> bool:
        """Check if filing date is within the specified range."""
        try:
            # Extract year from filing date (format: YYYY-MM-DD)
            year = int(filing_date.split('-')[0])
            return self.start_year <= year <= self.end_year
        except (ValueError, IndexError):
            logger.warning(f"Invalid date format: {filing_date}")
            return False
    
    def get_filing_document_url(self, accession_number: str, form_type: str) -> Optional[str]:
        """
        Get the URL for the primary document.
        
        Args:
            accession_number: SEC accession number for the filing
            form_type: Type of form (8-K, 10-Q, 10-K)
            
        Returns:
            URL to the primary document or None if not found
        """
        try:
            # Convert accession number to the format used in URLs
            accession_formatted = accession_number.replace('-', '')
            
            # Construct the filing index URL using the correct SEC format
            filing_index_url = f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{accession_formatted}/{accession_number}-index.html"
            
            logger.info(f"Fetching filing index: {accession_number}")
            
            # Use different headers for the www.sec.gov domain
            www_headers = {
                'User-Agent': 'AMD Research Tool (research@example.com)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(filing_index_url, headers=www_headers)
            response.raise_for_status()
            
            self._rate_limit()
            
            # Parse the HTML to find the primary document
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find the table with filing documents
            table = soup.find('table', class_='tableFile')
            if not table:
                logger.warning(f"No document table found for {accession_number}")
                return None
            
            # Look for the primary document of the specified form type
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all('td')
                if len(cells) >= 4:
                    doc_type = cells[3].get_text(strip=True)
                    # Look for documents of the specified form type (the first one is usually the primary)
                    if doc_type == form_type:
                        doc_link = cells[2].find('a')
                        if doc_link:
                            doc_filename = doc_link.get('href')
                            if doc_filename:
                                # Check if it's an interactive viewer link
                                if doc_filename.startswith('/ix?doc='):
                                    # Extract the actual document path from the interactive viewer URL
                                    actual_doc_path = doc_filename.split('doc=')[1]
                                    doc_url = f"https://www.sec.gov{actual_doc_path}"
                                else:
                                    # Direct link to document
                                    doc_url = f"https://www.sec.gov{doc_filename}"
                                return doc_url
            
            logger.warning(f"No primary {form_type} document found for {accession_number}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting document URL for {accession_number}: {e}")
            return None
    
    def download_filing(self, filing_info: Dict) -> Optional[str]:
        """
        Download a single filing and return the content.
        
        Args:
            filing_info: Dictionary containing filing information
            
        Returns:
            HTML content as string if successful, None otherwise
        """
        accession_number = filing_info['accession_number']
        filing_date = filing_info['filing_date']
        form_type = filing_info['form_type']
        
        # Get the document URL
        doc_url = self.get_filing_document_url(accession_number, form_type)
        if not doc_url:
            logger.error(f"Could not get document URL for {accession_number}")
            return None
        
        try:
            logger.info(f"Downloading filing from {filing_date}: {accession_number}")
            
            # Use appropriate headers for downloading documents
            www_headers = {
                'User-Agent': 'AMD Research Tool (research@example.com)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            # Download the document
            response = requests.get(doc_url, headers=www_headers)
            response.raise_for_status()
            
            self._rate_limit()
            
            logger.info(f"Downloaded: {form_type} {filing_date}.html")
            return response.text
            
        except Exception as e:
            logger.error(f"Failed to download {accession_number}: {e}")
            return None
    
    def download_all_filings(self) -> Dict[str, Dict[str, str]]:
        """
        Download all filings matching the criteria and return their content.
        
        Returns:
            Dictionary with form_type as key and nested dict with filing_date as key and HTML content as value
        """
        logger.info(f"Starting download of AMD filings for {self.start_year}-{self.end_year}")
        logger.info(f"Form types: {', '.join(self.form_types)}")
        
        # Get company submissions
        submissions_data = self.get_company_submissions()
        if not submissions_data:
            logger.error("Failed to get company submissions data")
            return {}
        
        # Filter filings by date range and form types
        filtered_filings = self.filter_filings_by_date_range(submissions_data)
        
        if not filtered_filings:
            logger.warning(f"No filings found for {self.start_year}-{self.end_year}")
            return {}
        
        # Download each filing and store content organized by form type
        downloaded_content = {}
        successful_downloads = 0
        failed_downloads = 0
        
        for filing_info in filtered_filings:
            content = self.download_filing(filing_info)
            if content:
                form_type = filing_info['form_type']
                filing_date = filing_info['filing_date']
                
                if form_type not in downloaded_content:
                    downloaded_content[form_type] = {}
                
                downloaded_content[form_type][filing_date] = content
                successful_downloads += 1
            else:
                failed_downloads += 1
        
        logger.info(f"Download complete. Total: {len(filtered_filings)}, "
                   f"Successful: {successful_downloads}, Failed: {failed_downloads}")
        
        return downloaded_content

# ============================================================================
# PART 2: CONTENT EXTRACTOR
# ============================================================================

class SECFilingsContentExtractor:
    def __init__(self):
        """
        Initialize the SEC filings content extractor.
        """
        self.extracted_data = {}
        
    def extract_from_content(self, html_content: str, filename: str, form_type: str) -> Dict[str, Any]:
        """
        Extract content from HTML content string.
        
        Args:
            html_content: HTML content as string
            filename: Name of the file (for logging)
            form_type: Type of form (8-K, 10-Q, 10-K)
            
        Returns:
            Dictionary containing extracted content
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract basic information
            extracted = {
                'filename': filename,
                'form_type': form_type,
                'filing_date': self._extract_filing_date(soup),
                'company_info': self._extract_company_info(soup),
                'form_info': self._extract_form_info(soup),
                'signatures': self._extract_signatures(soup),
                'main_content': self._extract_main_content(soup),
                'raw_text': self._extract_clean_text(soup)
            }
            
            # Extract form-specific content
            if form_type == '8-K':
                extracted['items'] = self._extract_8k_items(soup)
                extracted['exhibits'] = self._extract_exhibits(soup)
            elif form_type in ['10-Q', '10-K']:
                extracted['financial_statements'] = self._extract_financial_statements(soup)
                extracted['exhibits'] = self._extract_exhibits(soup)
                extracted['risk_factors'] = self._extract_risk_factors(soup)
            
            logger.info(f"Successfully extracted content from {filename}")
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting content from {filename}: {e}")
            return {'error': str(e), 'filename': filename}
    
    def _extract_filing_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the filing date from the document."""
        try:
            # Look for the filing date in various formats
            date_patterns = [
                r'Date of Report.*?(\w+ \d{1,2}, \d{4})',
                r'Date of earliest event reported.*?(\w+ \d{1,2}, \d{4})',
                r'(\w+ \d{1,2}, \d{4})',
            ]
            
            text = soup.get_text()
            for pattern in date_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            # Try to find in XBRL context
            context_elements = soup.find_all('xbrli:context')
            for context in context_elements:
                period = context.find('xbrli:period')
                if period:
                    end_date = period.find('xbrli:enddate')
                    if end_date:
                        return end_date.get_text()
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not extract filing date: {e}")
            return None
    
    def _extract_company_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract company information."""
        company_info = {}
        
        try:
            # Company name
            name_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityRegistrantName'})
            if name_elements:
                company_info['name'] = name_elements[0].get_text().strip()
            
            # CIK
            cik_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityCentralIndexKey'})
            if cik_elements:
                company_info['cik'] = cik_elements[0].get_text().strip()
            
            # Address
            address_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityAddressAddressLine1'})
            if address_elements:
                company_info['address'] = address_elements[0].get_text().strip()
            
            # City, State, ZIP
            city_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityAddressCityOrTown'})
            state_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityAddressStateOrProvince'})
            zip_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityAddressPostalZipCode'})
            
            if city_elements and state_elements and zip_elements:
                company_info['location'] = f"{city_elements[0].get_text().strip()}, {state_elements[0].get_text().strip()} {zip_elements[0].get_text().strip()}"
            
            # Phone
            phone_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:LocalPhoneNumber'})
            if phone_elements:
                company_info['phone'] = phone_elements[0].get_text().strip()
            
            # Trading symbol
            symbol_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:TradingSymbol'})
            if symbol_elements:
                company_info['trading_symbol'] = symbol_elements[0].get_text().strip()
            
            # Exchange
            exchange_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:SecurityExchangeName'})
            if exchange_elements:
                company_info['exchange'] = exchange_elements[0].get_text().strip()
            
        except Exception as e:
            logger.warning(f"Error extracting company info: {e}")
        
        return company_info
    
    def _extract_form_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract form-specific information."""
        form_info = {}
        
        try:
            # Document type
            doc_type_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:DocumentType'})
            if doc_type_elements:
                form_info['document_type'] = doc_type_elements[0].get_text().strip()
            
            # File number
            file_number_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityFileNumber'})
            if file_number_elements:
                form_info['file_number'] = file_number_elements[0].get_text().strip()
            
            # Tax ID
            tax_id_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityTaxIdentificationNumber'})
            if tax_id_elements:
                form_info['tax_id'] = tax_id_elements[0].get_text().strip()
            
            # State of incorporation
            state_elements = soup.find_all('ix:nonnumeric', {'name': 'dei:EntityIncorporationStateCountryCode'})
            if state_elements:
                form_info['state_of_incorporation'] = state_elements[0].get_text().strip()
            
        except Exception as e:
            logger.warning(f"Error extracting form info: {e}")
        
        return form_info
    
    def _extract_8k_items(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract 8-K items and their content."""
        items = []
        
        try:
            # Look for item headers
            item_pattern = r'Item\s+(\d+\.?\d*)\s*\.?\s*(.+)'
            
            # Find all divs that might contain items
            all_divs = soup.find_all('div')
            
            for div in all_divs:
                text = div.get_text().strip()
                match = re.match(item_pattern, text, re.IGNORECASE)
                
                if match:
                    item_number = match.group(1)
                    item_title = match.group(2).strip()
                    
                    # Extract content for this item
                    item_content = self._extract_item_content(div)
                    
                    items.append({
                        'item_number': item_number,
                        'title': item_title,
                        'content': item_content
                    })
            
        except Exception as e:
            logger.warning(f"Error extracting 8-K items: {e}")
        
        return items
    
    def _extract_financial_statements(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract financial statements from 10-Q/10-K forms."""
        financial_statements = []
        
        try:
            # Look for financial statement sections
            financial_patterns = [
                r'CONSOLIDATED\s+(?:STATEMENTS?\s+OF\s+)?(?:INCOME|OPERATIONS|CASH\s+FLOWS|FINANCIAL\s+POSITION)',
                r'BALANCE\s+SHEET',
                r'STATEMENT\s+OF\s+(?:INCOME|OPERATIONS|CASH\s+FLOWS)',
                r'CONDENSED\s+CONSOLIDATED\s+(?:STATEMENTS?|FINANCIAL\s+STATEMENTS?)'
            ]
            
            text = soup.get_text()
            for pattern in financial_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    start_pos = match.start()
                    # Extract a reasonable amount of text after the match
                    end_pos = min(start_pos + 2000, len(text))
                    statement_text = text[start_pos:end_pos]
                    
                    financial_statements.append({
                        'type': match.group(0),
                        'content': statement_text.strip()
                    })
            
        except Exception as e:
            logger.warning(f"Error extracting financial statements: {e}")
        
        return financial_statements
    
    def _extract_risk_factors(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract risk factors from 10-Q/10-K forms."""
        risk_factors = []
        
        try:
            # Look for risk factors section
            risk_pattern = r'RISK\s+FACTORS?'
            text = soup.get_text()
            
            match = re.search(risk_pattern, text, re.IGNORECASE)
            if match:
                start_pos = match.start()
                # Look for the next major section (usually starts with capital letters)
                next_section = re.search(r'\\n\\n[A-Z][A-Z\\s]{10,}\\n', text[start_pos + 100:])
                if next_section:
                    end_pos = start_pos + 100 + next_section.start()
                else:
                    end_pos = min(start_pos + 5000, len(text))
                
                risk_content = text[start_pos:end_pos]
                risk_factors.append({
                    'section': 'Risk Factors',
                    'content': risk_content.strip()
                })
            
        except Exception as e:
            logger.warning(f"Error extracting risk factors: {e}")
        
        return risk_factors
    
    def _extract_item_content(self, item_div) -> str:
        """Extract content for a specific item."""
        try:
            # Get all text from the item div and its siblings
            content_parts = []
            current = item_div
            
            # Get text from the current div
            content_parts.append(current.get_text().strip())
            
            # Look at following siblings for more content
            for sibling in current.find_next_siblings():
                if sibling.name == 'div':
                    text = sibling.get_text().strip()
                    # Stop if we hit another item
                    if re.match(r'Item\s+\d+\.?\d*', text, re.IGNORECASE):
                        break
                    if text:
                        content_parts.append(text)
            
            return '\n\n'.join(content_parts)
            
        except Exception as e:
            logger.warning(f"Error extracting item content: {e}")
            return ""
    
    def _extract_exhibits(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract exhibit information."""
        exhibits = []
        
        try:
            # Look for exhibit tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        # Check if this looks like an exhibit row
                        first_cell = cells[0].get_text().strip()
                        if re.match(r'\d+\.?\d*', first_cell):
                            exhibit_number = first_cell
                            description = cells[-1].get_text().strip()
                            
                            # Look for links
                            links = row.find_all('a')
                            link_url = links[0].get('href') if links else None
                            
                            exhibits.append({
                                'exhibit_number': exhibit_number,
                                'description': description,
                                'link': link_url
                            })
            
        except Exception as e:
            logger.warning(f"Error extracting exhibits: {e}")
        
        return exhibits
    
    def _extract_signatures(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract signature information."""
        signatures = {}
        
        try:
            # Look for signature section
            signature_section = soup.find('div', string=re.compile(r'SIGNATURE', re.IGNORECASE))
            
            if signature_section:
                # Find the parent div and extract signature info
                parent = signature_section.find_parent('div')
                if parent:
                    text = parent.get_text()
                    
                    # Extract date
                    date_match = re.search(r'Date:\s*([^\\n]+)', text)
                    if date_match:
                        signatures['date'] = date_match.group(1).strip()
                    
                    # Extract signatory name
                    name_match = re.search(r'Name:\s*([^\\n]+)', text)
                    if name_match:
                        signatures['name'] = name_match.group(1).strip()
                    
                    # Extract title
                    title_match = re.search(r'Title:\s*([^\\n]+)', text)
                    if title_match:
                        signatures['title'] = title_match.group(1).strip()
            
        except Exception as e:
            logger.warning(f"Error extracting signatures: {e}")
        
        return signatures
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract the main content of the 8-K."""
        try:
            # Remove XBRL header and other non-content elements
            for element in soup.find_all(['ix:header', 'script', 'style']):
                element.decompose()
            
            # Get all text content
            text = soup.get_text()
            
            # Clean up the text
            lines = text.split('\n')
            cleaned_lines = []
            
            for line in lines:
                line = line.strip()
                if line and len(line) > 10:  # Filter out very short lines
                    cleaned_lines.append(line)
            
            return '\n'.join(cleaned_lines)
            
        except Exception as e:
            logger.warning(f"Error extracting main content: {e}")
            return ""
    
    def _extract_clean_text(self, soup: BeautifulSoup) -> str:
        """Extract clean, readable text from the document."""
        try:
            # Remove all XBRL and technical elements
            for element in soup.find_all(['ix:header', 'ix:nonnumeric', 'ix:references', 'ix:resources', 'script', 'style']):
                element.decompose()
            
            # Get text and clean it up
            text = soup.get_text()
            
            # Remove excessive whitespace
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Error extracting clean text: {e}")
            return ""
    
    def extract_all_filings(self, downloaded_content: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Any]]:
        """
        Extract content from all downloaded HTML content.
        
        Args:
            downloaded_content: Dictionary with form_type as key and nested dict with filing_date as key and HTML content as value
            
        Returns:
            Dictionary with filename as key and extracted content as value
        """
        if not downloaded_content:
            logger.warning("No content to extract")
            return {}
        
        total_files = sum(len(filings) for filings in downloaded_content.values())
        logger.info(f"Processing {total_files} HTML files across {len(downloaded_content)} form types")
        
        for form_type, filings in downloaded_content.items():
            logger.info(f"Processing {len(filings)} {form_type} filings")
            for filing_date, html_content in filings.items():
                filename = f"{form_type}_{filing_date}.html"
                extracted_content = self.extract_from_content(html_content, filename, form_type)
                self.extracted_data[filename] = extracted_content
        
        logger.info(f"Successfully processed {len(self.extracted_data)} files")
        return self.extracted_data

# ============================================================================
# PART 3: TEXT CONVERTER
# ============================================================================

class TextConverter:
    def __init__(self):
        """
        Initialize the text converter.
        """
        self.data = {}
        
    def load_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load the extracted content from the extractor."""
        self.data = extracted_data
        return self.data
    
    def extract_text_values(self, obj: Any, path: str = "") -> List[str]:
        """
        Recursively extract all text values from a JSON object.
        
        Args:
            obj: The JSON object to extract text from
            path: Current path in the JSON structure
            
        Returns:
            List of text values found
        """
        text_values = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                text_values.extend(self.extract_text_values(value, current_path))
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                text_values.extend(self.extract_text_values(item, current_path))
        
        elif isinstance(obj, str) and obj.strip():
            # Add the text value with its path for context
            text_values.append(f"{path}: {obj.strip()}")
        
        return text_values
    
    def create_structured_txt_file(self, filename: str, content: Dict[str, Any], output_dir: str = "amd_filings_text_files") -> None:
        """
        Create a structured text file with organized sections.
        
        Args:
            filename: The HTML filename (e.g., "8-K_2023-01-11.html")
            content: The extracted content for this file
            output_dir: Directory to save the text files
        """
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Generate output filename
        base_name = filename.replace('.html', '')
        output_filename = f"{base_name}.txt"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            form_type = content.get('form_type', 'Unknown')
            f.write(f"AMD {form_type} Filing Content: {filename}\n")
            f.write("=" * 80 + "\n\n")
            
            # Basic Information
            f.write("BASIC INFORMATION\n")
            f.write("-" * 40 + "\n")
            f.write(f"Filename: {content.get('filename', 'N/A')}\n")
            f.write(f"Form Type: {form_type}\n")
            f.write(f"Filing Date: {content.get('filing_date', 'N/A')}\n\n")
            
            # Company Information
            f.write("COMPANY INFORMATION\n")
            f.write("-" * 40 + "\n")
            company_info = content.get('company_info', {})
            for key, value in company_info.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Form Information
            f.write("FORM INFORMATION\n")
            f.write("-" * 40 + "\n")
            form_info = content.get('form_info', {})
            for key, value in form_info.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Form-specific content
            if form_type == '8-K':
                # 8-K Items
                f.write("8-K ITEMS\n")
                f.write("-" * 40 + "\n")
                items = content.get('items', [])
                for i, item in enumerate(items, 1):
                    f.write(f"Item {item.get('item_number', 'N/A')}: {item.get('title', 'N/A')}\n")
                    f.write(f"Content: {item.get('content', 'N/A')}\n")
                    f.write("-" * 20 + "\n")
                f.write("\n")
            elif form_type in ['10-Q', '10-K']:
                # Financial Statements
                f.write("FINANCIAL STATEMENTS\n")
                f.write("-" * 40 + "\n")
                financial_statements = content.get('financial_statements', [])
                for statement in financial_statements:
                    f.write(f"Type: {statement.get('type', 'N/A')}\n")
                    f.write(f"Content: {statement.get('content', 'N/A')}\n")
                    f.write("-" * 20 + "\n")
                f.write("\n")
                
                # Risk Factors
                f.write("RISK FACTORS\n")
                f.write("-" * 40 + "\n")
                risk_factors = content.get('risk_factors', [])
                for risk in risk_factors:
                    f.write(f"Section: {risk.get('section', 'N/A')}\n")
                    f.write(f"Content: {risk.get('content', 'N/A')}\n")
                    f.write("-" * 20 + "\n")
                f.write("\n")
            
            # Exhibits
            f.write("EXHIBITS\n")
            f.write("-" * 40 + "\n")
            exhibits = content.get('exhibits', [])
            for exhibit in exhibits:
                f.write(f"Exhibit {exhibit.get('exhibit_number', 'N/A')}: {exhibit.get('description', 'N/A')}\n")
                if exhibit.get('link'):
                    f.write(f"Link: {exhibit.get('link')}\n")
                f.write("\n")
            
            # Signatures
            f.write("SIGNATURES\n")
            f.write("-" * 40 + "\n")
            signatures = content.get('signatures', {})
            for key, value in signatures.items():
                f.write(f"{key.replace('_', ' ').title()}: {value}\n")
            f.write("\n")
            
            # Main Content
            f.write("MAIN CONTENT\n")
            f.write("-" * 40 + "\n")
            main_content = content.get('main_content', '')
            if main_content:
                f.write(main_content)
            f.write("\n\n")
            
            # Raw Text
            f.write("RAW TEXT\n")
            f.write("-" * 40 + "\n")
            raw_text = content.get('raw_text', '')
            if raw_text:
                f.write(raw_text)
        
        logger.info(f"Created structured file: {output_path}")
    
    def convert_all_to_text(self) -> None:
        """Convert all extracted content to structured text files."""
        if not self.data:
            logger.error("No data to convert")
            return
        
        logger.info(f"Converting {len(self.data)} files to text format...")
        
        for filename, content in self.data.items():
            if 'error' in content:
                logger.warning(f"Skipping {filename}: {content['error']}")
                continue
            
            self.create_structured_txt_file(filename, content)
        
        logger.info("Text conversion complete!")

# ============================================================================
# PART 4: ANALYSIS AND REPORTING
# ============================================================================

class ContentAnalyzer:
    def __init__(self):
        """
        Initialize the content analyzer.
        """
        self.data = {}
        
    def load_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Load the extracted content from the extractor."""
        self.data = extracted_data
        return self.data
    
    def analyze_filing_dates(self) -> None:
        """Analyze filing dates and frequency."""
        print("\n" + "="*60)
        print("FILING DATE ANALYSIS")
        print("="*60)
        
        dates = []
        for filename, content in self.data.items():
            if 'filing_date' in content:
                dates.append(content['filing_date'])
                print(f"{filename}: {content['filing_date']}")
        
        print(f"\nTotal filings: {len(dates)}")
        if dates:
            print(f"Date range: {min(dates)} to {max(dates)}")
    
    def analyze_items(self) -> None:
        """Analyze 8-K items and their frequency."""
        print("\n" + "="*60)
        print("8-K ITEMS ANALYSIS")
        print("="*60)
        
        item_counter = Counter()
        item_details = defaultdict(list)
        
        for filename, content in self.data.items():
            if content.get('form_type') == '8-K':
                items = content.get('items', [])
                for item in items:
                    item_number = item.get('item_number', 'Unknown')
                    item_title = item.get('title', 'Unknown')
                    item_counter[item_number] += 1
                    item_details[item_number].append({
                        'filename': filename,
                        'title': item_title
                    })
        
        if item_counter:
            print("Item frequency:")
            for item_num, count in item_counter.most_common():
                print(f"  Item {item_num}: {count} occurrences")
            
            print("\nDetailed breakdown:")
            for item_num, details in item_details.items():
                print(f"\nItem {item_num}:")
                for detail in details:
                    print(f"  - {detail['filename']}: {detail['title'][:80]}...")
        else:
            print("No 8-K items found in the data.")
    
    def analyze_exhibits(self) -> None:
        """Analyze exhibits and their types."""
        print("\n" + "="*60)
        print("EXHIBITS ANALYSIS")
        print("="*60)
        
        exhibit_types = Counter()
        total_exhibits = 0
        
        for filename, content in self.data.items():
            exhibits = content.get('exhibits', [])
            total_exhibits += len(exhibits)
            
            for exhibit in exhibits:
                description = exhibit.get('description', '')
                # Categorize exhibit types
                if 'press release' in description.lower():
                    exhibit_types['Press Release'] += 1
                elif 'offer letter' in description.lower() or 'agreement' in description.lower():
                    exhibit_types['Agreements/Letters'] += 1
                elif 'presentation' in description.lower():
                    exhibit_types['Presentations'] += 1
                elif 'xbrl' in description.lower():
                    exhibit_types['XBRL'] += 1
                else:
                    exhibit_types['Other'] += 1
        
        print(f"Total exhibits across all filings: {total_exhibits}")
        print("\nExhibit types:")
        for exhibit_type, count in exhibit_types.most_common():
            print(f"  {exhibit_type}: {count}")
    
    def analyze_content_themes(self) -> None:
        """Analyze content themes and topics."""
        print("\n" + "="*60)
        print("CONTENT THEMES ANALYSIS")
        print("="*60)
        
        themes = {
            'Financial Results': 0,
            'Executive Changes': 0,
            'Compensation': 0,
            'Regulation FD': 0,
            'Risk Factors': 0,
            'Other': 0
        }
        
        for filename, content in self.data.items():
            form_type = content.get('form_type', '')
            
            if form_type == '8-K':
                items = content.get('items', [])
                for item in items:
                    title = item.get('title', '').lower()
                    content_text = item.get('content', '').lower()
                    
                    if 'results of operations' in title or 'financial condition' in title:
                        themes['Financial Results'] += 1
                    elif 'departure' in title or 'appointment' in title or 'election' in title:
                        themes['Executive Changes'] += 1
                    elif 'compensatory' in title or 'compensation' in content_text:
                        themes['Compensation'] += 1
                    elif 'regulation fd' in title:
                        themes['Regulation FD'] += 1
                    else:
                        themes['Other'] += 1
            elif form_type in ['10-Q', '10-K']:
                # Count risk factors
                risk_factors = content.get('risk_factors', [])
                themes['Risk Factors'] += len(risk_factors)
                
                # Count financial statements
                financial_statements = content.get('financial_statements', [])
                themes['Financial Results'] += len(financial_statements)
        
        print("Content themes:")
        for theme, count in themes.items():
            print(f"  {theme}: {count}")
    
    def analyze_financial_statements(self) -> None:
        """Analyze financial statements from 10-Q/10-K forms."""
        print("\n" + "="*60)
        print("FINANCIAL STATEMENTS ANALYSIS")
        print("="*60)
        
        statement_types = Counter()
        total_statements = 0
        
        for filename, content in self.data.items():
            if content.get('form_type') in ['10-Q', '10-K']:
                financial_statements = content.get('financial_statements', [])
                total_statements += len(financial_statements)
                
                for statement in financial_statements:
                    statement_type = statement.get('type', 'Unknown')
                    statement_types[statement_type] += 1
        
        print(f"Total financial statements found: {total_statements}")
        print("\nStatement types:")
        for stmt_type, count in statement_types.most_common():
            print(f"  {stmt_type}: {count}")
    
    def analyze_risk_factors(self) -> None:
        """Analyze risk factors from 10-Q/10-K forms."""
        print("\n" + "="*60)
        print("RISK FACTORS ANALYSIS")
        print("="*60)
        
        total_risk_sections = 0
        risk_factors_by_form = Counter()
        
        for filename, content in self.data.items():
            form_type = content.get('form_type', '')
            if form_type in ['10-Q', '10-K']:
                risk_factors = content.get('risk_factors', [])
                total_risk_sections += len(risk_factors)
                risk_factors_by_form[form_type] += len(risk_factors)
        
        print(f"Total risk factor sections found: {total_risk_sections}")
        print("\nRisk factors by form type:")
        for form_type, count in risk_factors_by_form.most_common():
            print(f"  {form_type}: {count} sections")
    
    def analyze_company_info(self) -> None:
        """Analyze company information consistency."""
        print("\n" + "="*60)
        print("COMPANY INFORMATION")
        print("="*60)
        
        # Get company info from first filing
        first_filing = list(self.data.values())[0]
        company_info = first_filing.get('company_info', {})
        
        print("Company Details:")
        print(f"  Name: {company_info.get('name', 'N/A')}")
        print(f"  CIK: {company_info.get('cik', 'N/A')}")
        print(f"  Address: {company_info.get('address', 'N/A')}")
        print(f"  Location: {company_info.get('location', 'N/A')}")
        print(f"  Phone: {company_info.get('phone', 'N/A')}")
        print(f"  Trading Symbol: {company_info.get('trading_symbol', 'N/A')}")
        print(f"  Exchange: {company_info.get('exchange', 'N/A')}")
    
    def generate_summary_report(self) -> None:
        """Generate a comprehensive summary report."""
        print("\n" + "="*80)
        print("AMD SEC FILINGS COMPREHENSIVE ANALYSIS REPORT")
        print("="*80)
        
        total_filings = len(self.data)
        
        # Count by form type
        form_type_counts = Counter()
        for content in self.data.values():
            form_type = content.get('form_type', 'Unknown')
            form_type_counts[form_type] += 1
        
        print(f"\nOVERVIEW:")
        print(f"  Total filings analyzed: {total_filings}")
        print(f"  Form type breakdown:")
        for form_type, count in form_type_counts.most_common():
            print(f"    {form_type}: {count} filings")
        
        # Count items, exhibits, financial statements, and risk factors
        total_items = sum(len(content.get('items', [])) for content in self.data.values() if content.get('form_type') == '8-K')
        total_exhibits = sum(len(content.get('exhibits', [])) for content in self.data.values())
        total_financial_statements = sum(len(content.get('financial_statements', [])) for content in self.data.values())
        total_risk_factors = sum(len(content.get('risk_factors', [])) for content in self.data.values())
        
        print(f"\nCONTENT BREAKDOWN:")
        print(f"  Total 8-K items: {total_items}")
        print(f"  Total exhibits: {total_exhibits}")
        print(f"  Total financial statements: {total_financial_statements}")
        print(f"  Total risk factor sections: {total_risk_factors}")
        
        if total_filings > 0:
            print(f"\nAVERAGES:")
            print(f"  Average exhibits per filing: {total_exhibits/total_filings:.1f}")
            if form_type_counts['8-K'] > 0:
                print(f"  Average 8-K items per filing: {total_items/form_type_counts['8-K']:.1f}")
            if form_type_counts['10-Q'] + form_type_counts['10-K'] > 0:
                print(f"  Average financial statements per 10-Q/10-K: {total_financial_statements/(form_type_counts['10-Q'] + form_type_counts['10-K']):.1f}")
        
        # Most common 8-K items
        item_counter = Counter()
        for content in self.data.values():
            if content.get('form_type') == '8-K':
                for item in content.get('items', []):
                    item_counter[item.get('item_number', 'Unknown')] += 1
        
        if item_counter:
            print(f"\nMOST COMMON 8-K ITEMS:")
            for item_num, count in item_counter.most_common(5):
                percentage = (count/form_type_counts['8-K']*100) if form_type_counts['8-K'] > 0 else 0
                print(f"  Item {item_num}: {count} filings ({percentage:.1f}%)")
        
        # Filing frequency by month
        month_counter = Counter()
        for content in self.data.values():
            filing_date = content.get('filing_date', '')
            if filing_date:
                # Extract month from date
                month = filing_date.split()[0] if filing_date else 'Unknown'
                month_counter[month] += 1
        
        print(f"\nFILING FREQUENCY BY MONTH:")
        for month, count in month_counter.most_common():
            print(f"  {month}: {count} filings")
    
    def run_full_analysis(self) -> None:
        """Run all analysis functions."""
        if not self.data:
            logger.error("No data to analyze")
            return
        
        print("AMD SEC Filings Content Analysis")
        print("=" * 50)
        
        self.analyze_filing_dates()
        self.analyze_items()
        self.analyze_exhibits()
        self.analyze_content_themes()
        self.analyze_financial_statements()
        self.analyze_risk_factors()
        self.analyze_company_info()
        self.generate_summary_report()
        
        print(f"\n[SUCCESS] Analysis complete! Analyzed {len(self.data)} SEC filings.")

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Main function to run the complete AMD SEC filings pipeline."""
    print("AMD SEC Filings Complete Pipeline")
    print("=" * 50)
    print("This script will:")
    print("1. Download AMD SEC filings (8-K, 10-Q, 10-K) for configured date range")
    print("2. Extract content using BeautifulSoup")
    print("3. Convert to structured text files only")
    print("4. Generate comprehensive analysis")
    print("=" * 50)
    
    # Load configuration
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        print(f"\nConfiguration loaded:")
        print(f"  Form types: {', '.join(config['download_settings']['form_types'])}")
        print(f"  Date range: {config['download_settings']['start_year']}-{config['download_settings']['end_year']}")
        print(f"  Output directory: {config['output_settings']['text_files_dir']}")
    except FileNotFoundError:
        print("Error: config.json not found. Please create a configuration file.")
        return
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in config.json: {e}")
        return
    
    # Step 1: Download SEC filings
    print("\n[STEP 1] Downloading AMD SEC filings...")
    downloader = AMDSECFilingsDownloader()
    downloaded_content = downloader.download_all_filings()
    
    if not downloaded_content:
        print("No files downloaded. Exiting.")
        return
    
    total_downloaded = sum(len(filings) for filings in downloaded_content.values())
    print(f"\nDownload Summary:")
    print(f"Successfully downloaded: {total_downloaded} filings")
    for form_type, filings in downloaded_content.items():
        print(f"  {form_type}: {len(filings)} filings")
    
    # Step 2: Extract content
    print("\n[STEP 2] Extracting content from HTML files...")
    extractor = SECFilingsContentExtractor()
    extracted_data = extractor.extract_all_filings(downloaded_content)
    
    if not extracted_data:
        print("No content extracted. Exiting.")
        return
    
    # Step 3: Convert to text files
    print("\n[STEP 3] Converting to structured text files...")
    converter = TextConverter()
    converter.load_data(extracted_data)
    converter.convert_all_to_text()
    
    # Step 4: Generate analysis
    if config['analysis_settings']['generate_analysis']:
        print("\n[STEP 4] Generating comprehensive analysis...")
        analyzer = ContentAnalyzer()
        analyzer.load_data(extracted_data)
        analyzer.run_full_analysis()
    
    print(f"\n[SUCCESS] Complete pipeline finished!")
    print(f"[INFO] Files created:")
    print(f"  - Text files: {config['output_settings']['text_files_dir']}/")
    print(f"[NOTE] HTML and JSON files are not saved - only structured text files are created.")

if __name__ == "__main__":
    main()
