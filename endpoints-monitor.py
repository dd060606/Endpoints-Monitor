import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
import os

# Regex pattern to capture various endpoint formats (based on https://github.com/GerbenJavado/LinkFinder)
regex_str = r"""
            (?:"|')                               # Start with a quote

            (
                # 1. Match full URLs with scheme or protocol-relative URLs
                ((?:[a-zA-Z]{1,10}://|//)         # Scheme or protocol-relative "//"
                [^"'/]{1,}\.                      # Domain name ending with a dot
                [a-zA-Z]{2,}[^"']{0,})            # Domain extension and path

                |

                # 2. Match relative paths starting with /, ./, or ../
                ((?:/|\.\./|\./)                  # Relative path symbols
                [^"'><,;| *()(%%$^/\\\[\]]        # Disallowed characters
                [^"'><,;|()]{1,})                 # Valid characters for path

                |

                # 3. Match relative endpoints with a file extension
                ([a-zA-Z0-9_\-/]{1,}/             # Path with /
                [a-zA-Z0-9_\-/.]{1,}              # File/resource name
                \.(?:[a-zA-Z]{1,4}|action)        # Extension (1-4 chars or 'action')
                (?:[\?|#][^"|']{0,}|))            # Optional query or fragment

                |

                # 4. Match REST-like endpoints without a file extension
                ([a-zA-Z0-9_\-/]{1,}/             # REST path ending with /
                [a-zA-Z0-9_\-/]{3,}               # At least 3+ characters for resource
                (?:[\?|#][^"|']{0,}|))            # Optional query or fragment

                |

                # 5. Match specific file types without preceding path symbols
                ([a-zA-Z0-9_\-]{1,}               # Filename
                \.(?:php|asp|aspx|jsp|json|       # Extension list
                     action|html|js|txt|xml)      # Common extensions
                (?:[\?|#][^"|']{0,}|))            # Optional query or fragment

            )

            (?:"|')                               # End with a quote
"""

def extract_js_files(url: str, headers = {}, cookies = {}) -> list[str]:
    # Parse the HTML content
    soup = BeautifulSoup(get_file_content(url, headers, cookies), 'html.parser')
        
    # Find all <script> tags with a src attribute
    js_files = []
    for script in soup.find_all('script', src=True):
        # Get the full URL of the JavaScript file
        js_url = urljoin(url, script['src'])
        js_files.append(js_url)
        
    return js_files


def get_file_content(url: str, headers = {}, cookies = {}) -> str:
    try:
        # Fetch the file content
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching the file: {e}")
        return ""

def extract_endpoints_from_js(js_content: str) -> list[str]:

    # Regular expression to capture endpoints
    # This regex captures full URLs, and paths that look like endpoints (e.g., "/api/", "/v1/")
    endpoint_pattern = re.compile(regex_str, re.VERBOSE | re.IGNORECASE)

    # Find all matches for endpoints
    endpoints = re.findall(endpoint_pattern, js_content)

    # Extract the first capturing group from each match
    endpoints = [match[0] for match in endpoints if match[0]]

    # Remove duplicates by converting to a set, then back to a list
    endpoints = list(set(endpoints))
        
    # Return the found endpoints
    return endpoints

def write_endpoints_to_file(endpoints: dict[str, list[str]] , output_file: str) -> None:
    with open(output_file, 'w') as f:
        for filename in endpoints.keys():
            f.write(f"[{filename}]: \n")
            for endpoint in endpoints[filename]:
                f.write(f"{endpoint}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url",
                        help="URL to monitor",
                        required="True")
    parser.add_argument("-H", "--headers", help="Headers to include in requests (e.g., 'User-Agent: Mozilla/5.0 ; CSRF-Token: TOKEN')", default="")
    parser.add_argument("-c", "--cookies", help="Cookies to include in requests (e.g, 'cookie1=aaaaaa; cookie2=bbbbbbbb')", default="")
    parser.add_argument("-o", "--output", help="Output directory to save the found endpoints", default="endpoints-output/")
    args = parser.parse_args()
    # Remove trailing slash from the URL
    if args.url[-1:] == "/":
        args.url = args.url[:-1]

    #Convert headers and cookies to a dictionary
    headers = dict(x.split(': ') for x in args.headers.split('; ')) if args.headers else {}
    cookies = dict(x.split('=') for x in args.cookies.split('; ')) if args.cookies else {}
    # Extract JavaScript files from the URL
    js_files = extract_js_files(args.url, headers, cookies)

    # Create output directory
    os.makedirs(args.output, exist_ok=True)

    # Extract endpoints from each JavaScript file
    endpoints = {}
    for js_file in js_files:
        js_content = get_file_content(js_file, headers, cookies)
        filename = os.path.basename(urlparse(js_file).path)
        endpoints[filename] = extract_endpoints_from_js(js_content)
        
    # Save the found endpoints to a file
    output_file = os.path.join(args.output, "latest_endpoints.txt")
    write_endpoints_to_file(endpoints, output_file)
