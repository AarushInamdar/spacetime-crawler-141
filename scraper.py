import re
from urllib.parse import urlparse, urljoin, urldefrag
from bs4 import BeautifulSoup

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
    
    # only process if the status code is 200 (OK).
    if resp.status != 200:
        return extracted_links
    
    try:
        # get the HTML content
        html_content = resp.raw_response.content
        
        #  parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all <a> tags and extract the href attribute
        for tag in soup.find_all('a'):
            href = tag.get('href')
            if href:
                # convert relative URLs to absolute URLs 
                absolute_url = urljoin(resp.url, href)
                # remove any URL fragment (e.g., the part after '#')
                absolute_url, _ = urldefrag(absolute_url)
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
    
    are considered valid.
    
    Parameters:
        url (str): The URL to be evaluated.
    
    Returns:
        bool: True if the URL is valid; False otherwise.
    """
    try:
        parsed = urlparse(url)
        
        # only allow HTTP and HTTPS URLs
        if parsed.scheme not in {"http", "https"}:
            return False
        
        # allowed domains (and subdomains)
        allowed_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]
        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            return False
        
        # filter out URLs with certain file extensions that are not useful.
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
        
        # URL passes all checks.
        return True

    except TypeError:
        print("TypeError encountered for URL:", url)
        return False
