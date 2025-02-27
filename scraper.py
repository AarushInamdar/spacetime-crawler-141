import re
import time
import logging
import hashlib
from urllib.parse import urlparse, urljoin, urldefrag, urlunparse, parse_qs, unquote
from collections import defaultdict
from bs4 import BeautifulSoup

# for tokenizing and computing frequencies
from tokenizer import Tokenizer
from tokenizer import STOPWORDS as stopwords

# --- Constants ---
MIN_HTML_SIZE = 1024
LARGE_PAGE_THRESHOLD = 5 * 1024 * 1024  # 5 MB threshold.
MIN_WORD_COUNT = 50                    # skip pages with fewer than 50 words.
SCRAPER_DELAY = 0.001 # additional politeness

# --- Logging configuration ---
logging.basicConfig(filename="output.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# --- Global state for duplicate detection and statistics ---
PAGE_CHECKSUMS = set()

class CrawlerStats:
    def __init__(self):
        self.unique_urls = set()
        self.longest_page = {"words": 0, "url": ""}
        self.ics_subdomains = defaultdict(int)
        self.frequent_words = defaultdict(int)

    def update_unique_urls(self, url: str):
        self.unique_urls.add(url)

    def update_longest_page(self, num_words: int, url: str):
        if num_words > self.longest_page["words"]:
            self.longest_page["words"] = num_words
            self.longest_page["url"] = url

    def check_and_update_ics_domain(self, url: str):
        parsed = urlparse(url)
        if parsed.netloc == "ics.uci.edu":
            self.ics_subdomains[parsed.netloc] += 1

    def update_frequent_words(self, tokens: list):
        freqs = tk.compute_word_frequencies(tokens)
        for token, count in freqs.items():
            if token not in stopwords:
                self.frequent_words[token] += count

    def get_top_50_words(self):
        sorted_items = sorted(self.frequent_words.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in sorted_items[:50]]

    def get_final_statistics(self):
        return {
            "num_unique_urls": len(self.unique_urls),
            "longest_page": self.longest_page["url"],
            "ics_subdomains": sorted(self.ics_subdomains.items()),
            "top_50_words": self.get_top_50_words()
        }

# global objects
stats = CrawlerStats()
tk = Tokenizer()

# --- Helper Functions ---
def _normalize_url(url: str) -> str:
    """Remove trailing slashes from the path to normalize the URL."""
    parsed = urlparse(url)
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip("/"),
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    return normalized

def _get_soup(resp) -> BeautifulSoup:
    """Return a BeautifulSoup object for the response content."""
    return BeautifulSoup(resp.raw_response.content, "html.parser")

import re

def _is_trap_url(url: str) -> bool:
  """Check whether a URL is a trap based on keywords, url patterns, or if there is a date trap pattern or filters"""
    lower_url = url.lower()
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # Trap Keywords
    trap_keywords = ["calendar", "ical", "archive", "revisions", "feed"]
    if any(keyword in lower_url for keyword in trap_keywords):
        return True

    # Detect "/YYYY-MM" or "/YYYY-MM-DD" anywhere in the URL (path or query)
    date_trap_pattern = re.compile(r'\b\d{4}-\d{2}(-\d{2})?\b')
    if date_trap_pattern.search(lower_url):
        return True

    # Check query parameters for encoded date patterns
    for param, values in query_params.items():
        for value in values:
            decoded_value = unquote(value)
            if date_trap_pattern.search(decoded_value):
                return True

    # block filtering queries
    if "?filter%" in lower_url:
        return True

    return False

# --- Main Functions ---
def scraper(url, resp):
    """
    Given a URL and the corresponding response from the cache server,
    extract all hyperlinks from the page (if the page is valid) and
    return only those URLs that are considered valid by is_valid.
    """
    logging.info(f"Scraping URL: {url}")
    logging.info(f"{stats.get_final_statistics()}")
    if resp is None or resp.raw_response is None:
        logging.info(f"Response is None for URL: {url}")
        return []
    if resp.status != 200:
        logging.info(f"Non-200 status ({resp.status}) for URL: {url}")
        return []
    
    html_content = resp.raw_response.content
    if not html_content or len(html_content) < MIN_HTML_SIZE:
        logging.info(f"Skipping {url} due to low data size ({len(html_content)} bytes).")
        return []
    
    # parse content once.
    soup = _get_soup(resp)
    page_text = soup.get_text(separator=" ", strip=True)
    tokens = tk.tokenize(page_text)
    
    # skip pages that have fewer than 50 words.
    if len(tokens) < MIN_WORD_COUNT:
        logging.info(f"Skipping {url}: too few words ({len(tokens)} tokens).")
        return []
    
    # Exact duplicate detection (before computing checksum)
    if page_text in EXACT_PAGE_CONTENTS:
        logging.info(f"Exact duplicate page detected at URL: {url}")
        return []
    EXACT_PAGE_CONTENTS.add(page_text)

    # compute checksum to avoid duplicate pages.
    checksum = hashlib.md5(page_text.encode("utf-8")).hexdigest()
    if checksum in PAGE_CHECKSUMS:
        logging.info(f"Duplicate page (checksum: {checksum}) detected at URL: {url}")
        return []
    PAGE_CHECKSUMS.add(checksum)
    
    # Skip pages that are too large.
    if len(html_content) > LARGE_PAGE_THRESHOLD:
        logging.info(f"Skipping {url}: page size {len(html_content)} exceeds threshold.")
        return []
    
    # Update global statistics.
    norm_url = _normalize_url(url)
    stats.update_unique_urls(norm_url)
    stats.update_longest_page(len(tokens), url)
    stats.check_and_update_ics_domain(url)
    stats.update_frequent_words(tokens)
    
    # Extract links from the page.
    links = extract_next_links(url, resp)
    time.sleep(SCRAPER_DELAY)
    valid_links = [link for link in links if is_valid(link)]
    return valid_links

def extract_next_links(url, resp):
    """
    Extracts and returns a list of hyperlinks from resp.raw_response.content.
    """
    extracted_links = []
    if resp.status != 200:
        return extracted_links

    try:
        html_content = resp.raw_response.content
        if not html_content or len(html_content) < MIN_HTML_SIZE:
            logging.info(f"Skipping link extraction for {url}: content too small.")
            return extracted_links

        soup = _get_soup(resp)
        seen = set()
        for tag in soup.find_all("a", href=True):
            href = tag.get("href")
            if href:
                absolute_url = urljoin(resp.url, href)
                absolute_url, _ = urldefrag(absolute_url)
                norm = _normalize_url(absolute_url)
                if norm == _normalize_url(resp.url):
                    continue  # Skip self-referential links.
                if norm not in seen:
                    seen.add(norm)
                    extracted_links.append(absolute_url)
    except Exception as e:
        logging.error(f"Error parsing page {url}: {e}")
    
    return extracted_links

def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False

        # Allowed domains must match exactly.
        allowed_domains = {"ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"}
        if parsed.netloc not in allowed_domains:
            return False

        # General trap detection: calendars, archives, date-based URLs, etc.
        if _is_trap_url(url):
            return False

        ext_pattern = re.compile(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            r"|epub|dll|cnf|tgz|sha1"
            r"|thmx|mso|arff|rtf|jar|csv"
            r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", re.IGNORECASE)
        if ext_pattern.match(parsed.path):
            return False

        if parsed.path.count('/') > 10:
            return False

        return True

    except Exception as e:
        logging.error(f"Error validating URL {url}: {e}")
        return False
