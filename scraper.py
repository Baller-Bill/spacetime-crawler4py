import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

def scraper(url, resp):
    links = extract_next_links(url, resp)
    return [link for link in links if is_valid(link)]

def extract_next_links(url, resp):
    # Implementation required.
    # url: the URL that was used to get the page
    # resp.url: the actual url of the page
    # resp.status: the status code returned by the server. 200 is OK, you got the page. Other numbers mean that there was some kind of problem.
    # resp.error: when status is not 200, you can check the error here, if needed.
    # resp.raw_response: this is where the page actually is. More specifically, the raw_response has two parts:
    #         resp.raw_response.url: the url, again
    #         resp.raw_response.content: the content of the page!
    # Return a list with the hyperlinks (as strings) scrapped from resp.raw_response.content

    # If response status is not 200-599 or raw_response is None, return an empty list
    urls = []
    if resp.status < 200 or resp.status >= 599 or resp.raw_response is None:
        return []
    
    try:
        soup = BeautifulSoup(resp.raw_response.content, 'html.parser')
    except Exception:
        # If HTML parsing fails
        return []

    # Extract all <a href="..."> links
    for link in soup.find_all('a', href=True):
        href = link.get('href')
        if href:
            # Convert relative URLs to absolute
            absolute_url = urljoin(url, href)
            urls.append(absolute_url)

    return urls

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        domain = parsed.netloc.lower()
        full_url = url.lower()
        query = parsed.query.lower()
        

        # Only crawl UCI domains
        if not re.match(
            r".*\.(ics\.uci\.edu|cs\.uci\.edu|informatics\.uci\.edu|stat\.uci\.edu)$",
            parsed.netloc.lower()
        ):
            return False
        
        if (
            "intranet.ics.uci.edu" in domain  # private/internal site
            or "doku.php" in path              # dynamic wiki engine
            or "do=" in query                  # doku command parameter
            or "tab_" in query                 # doku UI tab system
            or "image=" in query               # image manager
            or "ns=" in query                  # doku namespace
            or "calendar" in full_url
            or "ical" in full_url
            or "tribe" in full_url
            or "eppstein/pix" in full_url
            or "wics.ics.uci.edu" in domain
            or "ngs.ics.uci.edu" in domain
        ):
            return False
        
        if any(param in full_url for param in ["?share=", "?replytocom=", "?action="]):
            return False
        
        return not re.match(
            r".*\.(css|js|bmp|gif|jpe?g|ico"
            + r"|png|tiff?|mid|mp2|mp3|mp4"
            + r"|wav|avi|mov|mpeg|ram|m4v|mkv|ogg|ogv|pdf"
            + r"|ps|eps|tex|ppt|pptx|doc|docx|xls|xlsx|names"
            + r"|data|dat|exe|bz2|tar|msi|bin|7z|psd|dmg|iso"
            + r"|epub|dll|cnf|tgz|sha1"
            + r"|thmx|mso|arff|rtf|jar|csv"
            + r"|rm|smil|wmv|swf|wma|zip|rar|gz)$", parsed.path.lower())

        
    except TypeError:
        print ("TypeError for ", url)
        return False
