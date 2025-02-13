import re
import time
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup

# minimum HTML size threshold (in bytes) for a page to be considered informative
# pages below 1024 bytes are likely to be empty, error pages, or low-information traps.
MIN_HTML_SIZE = 1024

# extra scraper delay in case
SCRAPER_DELAY = 0.001

def scraper(url, resp):
    """
    Given a URL and the corresponding response from the cache server,
    extract all hyperlinks from the page (if the page is valid) and
    return only those URLs that are considered valid by is_valid.
    
    Parameters:
        url (str): The URL that was requested.
        resp: The response object containing:
            - resp.url: The final URL of the page (after redirection).
            - resp.status: The HTTP status code (200 is OK).
            - resp.raw_response.content: The HTML content of the page.
    
    Returns:
        A list of valid URLs (strings) extracted from the page.
    """
    links = extract_next_links(url, resp)
    # delay a little to reduce overall request rate.
    time.sleep(SCRAPER_DELAY)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    """
    Extracts and returns a list of hyperlinks from resp.raw_response.content.
    
    Parameters:
        url (str): The original URL used for the request.
        resp: The response object containing:
            - resp.url: The URL after any redirection.
            - resp.status: HTTP status code (200 indicates success).
            - resp.raw_response.content: The raw HTML content of the page.
    
    Returns:
        list: A list of URLs (strings) extracted from the page.
    """
    extracted_links = []
    
    # process only if the status code is 200 (OK).
    if resp.status != 200:
        return extracted_links
    
    try:
        html_content = resp.raw_response.content
        
        # skip processing if no content or not important size
        if not html_content or len(html_content) < MIN_HTML_SIZE:
            print(f"Skipping page {url} due to low data size ({len(html_content)} bytes).")
            return extracted_links
        
        # parsed the HTML content using BeautifulSoup.
        soup = BeautifulSoup(html_content, 'html.parser')
        
        #  set to store unique links.
        seen = set()
        for tag in soup.find_all('a'):
            href = tag.get('href')
            if href:
                absolute_url = urljoin(resp.url, href)
                # remove any URL fragment.
                absolute_url, _ = urldefrag(absolute_url)
                # avoid self-referential links.
                if absolute_url == resp.url:
                    continue
                # only add if not seen already.
                if absolute_url not in seen:
                    seen.add(absolute_url)
                    extracted_links.append(absolute_url)
                
    except Exception as e:
        print(f"Error parsing page {url}: {e}")
    
    return extracted_links

def is_valid(url):
    """
    Determines whether the given URL should be crawled.
    
    Only URLs that:
      - Use the http or https scheme,
      - Belong to the allowed domains,
      - Do not point to files with undesired extensions,
      - Do not exhibit suspicious patterns (e.g. excessive slashes),
    
    are considered valid.
    
    Parameters:
        url (str): The URL to be evaluated.
    
    Returns:
        bool: True if the URL is valid; False otherwise.
    """
    try:
        parsed = urlparse(url)
        
        # Only allow HTTP and HTTPS URLs.
        if parsed.scheme not in {"http", "https"}:
            return False
        
        # Allowed domains (and subdomains).
        allowed_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            return False
        
        # Filter out URLs with undesired file extensions.
        if re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            r"|png|tiff?|mid|mp2|mp3|mp4"
            r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            r"|epub|dll|cnf|tgz|sha1"
            r"|thmx|mso|arff|rtf|jar|csv"
            r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower()):
            return False
        
        # Avoid URLs with an excessive number of slashes.
        if parsed.path.count('/') > 10:
            return False
        
        return True

    except Exception as e:
        print("Error validating URL:", url, e)
        return False
