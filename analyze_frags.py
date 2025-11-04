

import shelve
from urllib.parse import urlparse

file_loc = "save_frags"

last_frag_file_num = 4

overall_save = shelve.open("crawler_data.shelve")
url_frag_dict = overall_save.get("url_frag_dict", {})

print(f"Total Unique Websites Crawled: {len(url_frag_dict.keys() )}")

longest_page_len = 0
longest_words_url = ""
url_total_words = overall_save.get("url_total_words", {})

subdomain_counts = {}

for key, value in url_total_words.items():
    parsed = urlparse(key)

    if parsed.netloc in subdomain_counts:
        subdomain_counts[parsed.netloc] += 1
    else:
        subdomain_counts[parsed.netloc] = 1

    if value > longest_page_len:
        longest_words_url = key
        longest_page_len = value

overall_save.close()

print(f"Page with the most words({longest_page_len} words): {longest_words_url}\n")

sorted_subdomain_counts = dict(sorted(subdomain_counts.items(), key=lambda item: item[0]))

print(f"Unique Subdomains: {len(subdomain_counts.keys())}\n")
print("Subdomain Counts:")
for key, value in sorted_subdomain_counts.items():
    print(f"\t{key}, {value}")

print()

most_common_tokens_dict = {}

for i in range(0,last_frag_file_num + 1):
    file_name = f"save_frags/save_frag_{i}.shelve"
    print("Analyzing Shelve File: " + file_name)
    frag_save = shelve.open(file_name)

    link_scanned_data = frag_save.get("link_scanned_data", {})

    for key, token_dict in link_scanned_data.items():

        if len(token_dict.keys()) < 15:
            continue

        for token, freq in token_dict.items():
            if token not in most_common_tokens_dict:
                most_common_tokens_dict[token] = freq
            else:
                most_common_tokens_dict[token] += freq
            
            if token == "markellekelly":
                print(f"Markelle Kelly URL: {key}")
    #print()


    frag_save.close()

top_50_tokens = dict(sorted(
    most_common_tokens_dict.items(), 
    key=lambda item: item[1],  # sort by value
    reverse=True               # descending order
)[:50])

print(f"Top 50 most common tokens:")
for key, value in top_50_tokens.items():
    print(f"\t{key}: {value}")