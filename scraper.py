import re
from urllib.parse import urlparse
from urllib.parse import urljoin
from urllib.parse import urlparse, urlunparse

import configparser
import time
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup
import nltk

from collections import Counter

#nltk.download('stopwords')
#nltk.download('punkt_tab')

from nltk.stem import WordNetLemmatizer
#nltk.download('wordnet')

from nltk.corpus import stopwords
import shelve

import atexit

config = configparser.ConfigParser()
config.read("config.ini")
USERAGENT = config.get("IDENTIFICATION", "USERAGENT", fallback="*")
DEFAULT_DELAY = config.get("CRAWLER", "POLITENESS")

STOPWORDS = set(stopwords.words('english'))

PATTERNS = [
    r".*\.ics\.uci\.edu/.*",
    r".*\.cs\.uci\.edu/.*",
    r".*\.informatics\.uci\.edu/.*",
    r".*\.stat\.uci\.edu/.*"
]

INVALID_DOMAINS = [
]

INVALID_PATTERNS = [
    re.compile(r".*/\d{4}/\d{2}/\d{2}/.*"),
    re.compile(r".*/\d{2}/\d{2}/\d{4}/.*"),
    re.compile(r".*/attachment/.*"),
    re.compile(r".*img_.*"),
    re.compile(r".*eppstein/pix.*")
]

PREFIX_COUNTER_LIMIT = 100
PREFIX_MAX_DEPTH = 2
SAVE_COUNTER_D = 1000
save_counter = SAVE_COUNTER_D
sync_counter = 50
MAX_TOKENS = 100
lemmatizer = WordNetLemmatizer()

SAVE_FILE = config.get("LOCAL PROPERTIES", "SAVE_2", fallback="crawler_data")
save = shelve.open(SAVE_FILE)

domain_delays = save.get("domain_delays", {})
prefix_counter = save.get("prefix_counter", {})
url_frag_dict = save.get("url_frag_dict", {})
save_file_num = save.get("save_file_num",0)

save_file_name = f"save_frags/save_frag_{save_file_num}.shelve" 

current_save_frag = shelve.open(save_file_name)
link_scanned_data = current_save_frag.get("link_scanned_data", {})



def scraper(url, resp):
    global save_counter
    global sync_counter
    global lemmatizer
    global link_scanned_data   # <-- add this line
    global current_save_frag
    global save_file_name
    global save_file_num
    global SAVE_COUNTER_D

    status = getattr(resp, "status", None)
    if not resp or status != 200 or not getattr(resp, "raw_response", None):
        print(f"Skipping {url} — invalid response (status={status})")
        return []

    # Second check: skip non-HTML content, but safely handle missing headers
    if not (resp.raw_response and getattr(resp.raw_response, "headers", {}).get("Content-Type", "").startswith("text/html")):
        print(f"Skipping non-HTML content: {url}")
        return []
        

    normalized = normalize_url(url)

    soup = BeautifulSoup(resp.raw_response.content, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    text = soup.get_text(separator=" ")
    tokens_pre_stop = nltk.tokenize.word_tokenize(text.lower())

    filtered_tokens = []

    for token in tokens_pre_stop:
        token = token.lower()
        if token.isalpha() and token not in STOPWORDS:
            t = lemmatizer.lemmatize(token)
            filtered_tokens.append(t)


    if len(filtered_tokens) < 10:
        return []

    # Count frequencies
    word_counts = Counter(filtered_tokens)

    #top_tokens = dict(word_counts.most_common(MAX_TOKENS))

    # Store the compact dictionary of counts
    link_scanned_data[url] = word_counts
    url_frag_dict[url] = save_file_name

    sync_counter -= 1

    if sync_counter == 0:
        sync_counter = 50
        save_data()
        current_save_frag["link_scanned_data"] = link_scanned_data
        current_save_frag.sync()

    save_counter -= 1
    if save_counter == 0:
        save_counter = SAVE_COUNTER_D

        save_data()
        save_file_num += 1
        save_frag_data() #will close current frag file

        save_file_name = f"save_frags/save_frag_{save_file_num}.shelve" 
        current_save_frag = shelve.open(save_file_name)
        link_scanned_data = {}
        

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

    links = []


    soup = BeautifulSoup(resp.raw_response.content, "lxml")

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]

        potential_link = urljoin(resp.raw_response.url ,href) 

        parsed = urlparse(potential_link)
        defragged = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))

        links.append(normalize_url(defragged))

    return links

def is_valid(url):
    # Decide whether to crawl this url or not. 
    # If you decide to crawl it, return True; otherwise return False.
    # There are already some conditions that return False.
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        normalized = normalize_url(url)

        if url in url_frag_dict:
            return False

        matches_patterns = False
        for pattern in PATTERNS:
            if re.match(pattern, normalized):
                matches_patterns = True
        if not matches_patterns:
            return False
        
        netloc = parsed.netloc.lower()
        for invalid in INVALID_DOMAINS:
            if re.search(invalid, netloc):
                return False
        
        for invalid_pattern in INVALID_PATTERNS:
            if re.match(invalid_pattern, normalized):
                return False
        
        prefix_depth = get_prefix_depth(normalized)
        for i in range(1, min( prefix_depth , PREFIX_MAX_DEPTH) + 1):
            key = get_url_prefix(normalized, i)
            if key in prefix_counter:
                prefix_counter[key] += 1
                if prefix_counter[key] >= PREFIX_COUNTER_LIMIT:
                    return False
            else:
                prefix_counter[key] = 1
        
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
        print ("TypeError for ", parsed)
        raise

def normalize_url(url):
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = re.sub(r"/+", "/", parsed.path)  # collapse multiple slashes
    if path.endswith("/") and path != "/":
        path = path[:-1]  # remove trailing slash
    return urlunparse((scheme, netloc, path, "", "", ""))

def get_url_prefix(url, depth):
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    prefix = "/".join(parts[:depth])
    normalized_netloc = parsed.netloc.lower()
    return f"{normalized_netloc}/{prefix}" if prefix else normalized_netloc

def get_prefix_depth(url):
    parsed = urlparse(url)
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    return len(parts)

def save_data():
    global save, url_frag_dict, prefix_counter, save_file_num
    #save["domain_delays"] = domain_delays
    save["url_frag_dict"] = url_frag_dict
    save["prefix_counter"] = prefix_counter
    save["save_file_num"] = save_file_num

    save.sync()

def save_frag_data():
    global current_save_frag, link_scanned_data
    current_save_frag["link_scanned_data"] = link_scanned_data
    current_save_frag.sync()
    current_save_frag.close()

def close_shelf():
    save_data()
    save.close()
    save_frag_data()

atexit.register(close_shelf)