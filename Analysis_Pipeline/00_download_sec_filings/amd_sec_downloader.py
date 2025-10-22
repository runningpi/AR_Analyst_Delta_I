#!/usr/bin/env python3
"""
AMD SEC Filings Downloader - Improved Version

This script downloads AMD SEC filings by form type and time span, converts to Markdown.
Based on the improved logic from the notebook.

Required:
  pip install requests beautifulsoup4 lxml pandas

Examples:
  python amd_sec_downloader.py --forms 10-Q 10-K --start 2022 --end 2024
"""

import argparse
import os
import time
import re
import requests
from pathlib import Path
from typing import Iterable, List, Dict, Any
import pandas as pd
from bs4 import BeautifulSoup
import logging
from io import StringIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CIK_DEFAULT = "0000002488"  # AMD
SUBMISSIONS_TMPL = "https://data.sec.gov/submissions/CIK{CIK}.json"
HIST_TMPL = "https://data.sec.gov/submissions/{name}"
ARCHIVE_TMPL = "https://www.sec.gov/Archives/edgar/data/{cik_nozero}/{acc_nodash}/{primary}"

HEADERS = {
    "User-Agent": "AMD Research Tool contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}

def parse_args():
    p = argparse.ArgumentParser(description="Fetch SEC filings and save as Markdown")
    p.add_argument("--forms", nargs="+", required=True, help="Form types, e.g. 10-Q 10-K")
    p.add_argument("--start", type=int, required=True, help="Start year inclusive")
    p.add_argument("--end", type=int, required=True, help="End year inclusive")
    p.add_argument("--cik", default=CIK_DEFAULT, help="Company CIK with leading zeros")
    p.add_argument("--outdir", default="filings_markdown", help="Output directory for .md files")
    p.add_argument("--sleep", type=float, default=0.25, help="Pause between requests in seconds")
    return p.parse_args()

def year_in_range(date_str: str, start_y: int, end_y: int) -> bool:
    try:
        y = int(date_str.split("-")[0])
        return start_y <= y <= end_y
    except Exception:
        return False

def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.]+", "_", s)

def fetch_json(url: str) -> Dict[str, Any]:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()

def iter_all_filings(cik: str) -> Iterable[Dict[str, Any]]:
    """
    Yield dicts with keys: form, filingDate, accessionNumber, primaryDocument
    Includes both recent and historical filing sets under submissions files
    """
    subs_url = SUBMISSIONS_TMPL.format(CIK=cik)
    root = fetch_json(subs_url)
    recent = root.get("filings", {}).get("recent", {})
    n = min(len(recent.get("form", [])),
            len(recent.get("filingDate", [])),
            len(recent.get("accessionNumber", [])),
            len(recent.get("primaryDocument", [])))
    for i in range(n):
        yield {
            "form": recent["form"][i],
            "filingDate": recent["filingDate"][i],
            "accessionNumber": recent["accessionNumber"][i],
            "primaryDocument": recent["primaryDocument"][i],
        }

    hist_files = root.get("filings", {}).get("files", []) or []
    for f in hist_files:
        name = f.get("name")
        if not name:
            continue
        try:
            j = fetch_json(HIST_TMPL.format(name=name))
        except Exception:
            continue
        data = j.get("filings", {}).get("recent", {})
        m = min(len(data.get("form", [])),
                len(data.get("filingDate", [])),
                len(data.get("accessionNumber", [])),
                len(data.get("primaryDocument", [])))
        for i in range(m):
            yield {
                "form": data["form"][i],
                "filingDate": data["filingDate"][i],
                "accessionNumber": data["accessionNumber"][i],
                "primaryDocument": data["primaryDocument"][i],
            }

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def unwrap_ixbrl(soup: BeautifulSoup):
    for tag in list(soup.find_all()):
        name = tag.name or ""
        if isinstance(name, str) and name.lower().startswith("ix:"):
            tag.unwrap()

def html_to_markdown(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    for bad in soup(["script", "style", "noscript", "template", "header", "footer", "nav"]):
        bad.decompose()

    unwrap_ixbrl(soup)

    for br in soup.find_all("br"):
        br.replace_with("\n")

    title = soup.find(["h1", "h2", "title"])
    title_text = clean(title.get_text()) if title else "SEC Filing"

    tables_md: List[str] = []
    try:
        for i, df in enumerate(pd.read_html(StringIO(str(soup))), 1):
            df.columns = [clean(str(c)) for c in df.columns]
            tables_md.append(f"### Tabelle {i}\n\n" + df.to_markdown(index=False) + "\n")
    except ValueError:
        pass

    text_blocks: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "div"]):
        txt = clean(tag.get_text(separator=" "))
        if not txt:
            continue
        if tag.name in {"h1", "h2", "h3"} or len(txt) >= 20:
            text_blocks.append(txt)

    seen = set()
    uniq_blocks = []
    for t in text_blocks:
        if t in seen:
            continue
        seen.add(t)
        uniq_blocks.append(t)

    parts = [f"# {title_text}\n"]
    if tables_md:
        parts.append("## Tabellen")
        parts.extend(tables_md)
    parts.append("## Text")
    parts.append("\n\n".join(uniq_blocks[:400]))

    return "\n".join(parts)

def download_and_convert(cik: str, forms: List[str], start_y: int, end_y: int,
                         outdir: Path, pause: float) -> int:
    outdir.mkdir(parents=True, exist_ok=True)
    total = 0

    for item in iter_all_filings(cik):
        form = item.get("form", "")
        date = item.get("filingDate", "")
        acc = item.get("accessionNumber", "")
        prim = item.get("primaryDocument", "")

        if form not in forms:
            continue
        if not year_in_range(date, start_y, end_y):
            continue
        if not acc or not prim:
            continue

        acc_nodash = acc.replace("-", "")
        url = ARCHIVE_TMPL.format(
            cik_nozero=int(cik),
            acc_nodash=acc_nodash,
            primary=prim
        )
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60)
            if resp.status_code != 200:
                logger.warning(f"Skip {resp.status_code} {url}")
                time.sleep(pause)
                continue
            md = html_to_markdown(resp.text)
            fname = safe_name(f"{form}_{date}_{acc}_{prim}") + ".md"
            (outdir / fname).write_text(md, encoding="utf-8")
            logger.info(f"Saved {fname}")
            total += 1
        except Exception as e:
            logger.error(f"Error for {url}: {e}")
        time.sleep(pause)
    return total

def main():
    args = parse_args()
    total = download_and_convert(
        cik=args.cik,
        forms=args.forms,
        start_y=args.start,
        end_y=args.end,
        outdir=Path(args.outdir),
        pause=args.sleep,
    )
    logger.info(f"Done total {total} files")

if __name__ == "__main__":
    main()
