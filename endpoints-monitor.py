import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import argparse
import os
from datetime import date


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

def extract_endpoints_from_js(js_content: str, filter_enabled: bool = False) -> list[str]:
    # Regular expression to capture endpoints
    # This regex captures full URLs, and paths that look like endpoints (e.g., "/api/", "/v1/")
    endpoint_pattern = re.compile(regex_str, re.VERBOSE | re.IGNORECASE)

    # Find all matches for endpoints
    endpoints = re.findall(endpoint_pattern, js_content)

    if filter_enabled:
        # Filter out common file extensions if enabled
        disallowed_extensions = (".png", ".jpg", ".jpeg", ".gif", ".svg",".webp", ".ico", ".css", ".json")
        endpoints = [match[0] for match in endpoints if match[0] and not match[0].endswith(disallowed_extensions)]
    else:
        # Extract the first capturing group from each match
        endpoints = [match[0] for match in endpoints if match[0]]

    # Remove duplicates by converting to a set, then back to a list
    endpoints = list(set(endpoints))
        
    # Return the found endpoints
    return endpoints

def diff_endpoints(old_endpoints: dict[str, list[str]], new_endpoints: dict[str, list[str]]) -> dict[str, list[str]]:
    # Find the differences between the old and new endpoints
    diff = {}
    for category, new_list in new_endpoints.items():
        old_list = old_endpoints.get(category, [])
        # Find the endpoints that are in the new list but not in the old list
        added = list(set(new_list) - set(old_list))
        if added:
            diff[category] = added
    return diff
    
def notify_discord_webhook(webhook_url: str, new_endpoints: dict[str, list[str]], latest_endpoints_file: str, target_hostname: str) -> None:
    diff = diff_endpoints(read_endpoints_from_file(latest_endpoints_file), new_endpoints)
    # If there are no new endpoints, return early
    if diff == {}:
        return
    # Prepare the payload for the Discord webhook
    fields = []
    for category in diff.keys():
        fields.append({"name": category, "value": ""})
    payload = {"content": "", "embeds": [{
        "title": f"New Endpoints Found - {target_hostname}",
        "color":1683176,
         "fields": fields,
        "footer": {
            "text": f"Check the results in the HTML file: {hostname.replace(".", "-")}.html",
        }
    }]}
    try:
        # Send a POST request to the Discord webhook URL
        response = requests.post(webhook_url, headers={'Content-Type': 'application/json'},json=payload)
        response.raise_for_status()
        print(response.text)
        return response.text
    except requests.RequestException as e:
        print(f"Error while sending a notification to Discord: {e}")
        return ""


def read_endpoints_from_file(file: str) -> dict[str, list[str]]:
    # Read existing content if the file exists
    try:
        with open(file, 'r') as f:
            file_content = f.read()
            # Extract categories and endpoints from the file content
            js_categories = re.findall(r"\[(.*)\]:", file_content)
            splitted_endpoints = re.split(r"\[.*\]:", file_content)[1:]
            # Create a dictionary of categories and endpoints
            old_endpoints = {}
            for category, endpoints in zip(js_categories, splitted_endpoints):
                old_endpoints[category] = endpoints.split("\n")[1:-1]
            return old_endpoints
    except Exception:
        return {}

def write_endpoints_to_file(new_endpoints: dict[str, list[str]] , output_file: str) -> None:
    # Update the file with the new endpoints
    old_endpoints = read_endpoints_from_file(output_file)
    diff = diff_endpoints(old_endpoints, new_endpoints)
    # Combine old and new endpoints by adding any new ones found in the diff
    for category, new_list in diff.items():
        if category in old_endpoints:
            old_endpoints[category].extend(new_list)
            # Remove duplicates
            old_endpoints[category] = list(set(old_endpoints[category]))
        else:
            old_endpoints[category] = new_list

    # Write the updated endpoints to the file
    with open(output_file, 'w') as f:
        for category, endpoints_list in old_endpoints.items():
            f.write(f"[{category}]:\n")
            for endpoint in endpoints_list:
                f.write(f"{endpoint}\n")

def get_urls_from_input(input:str) -> list[str]:
    # Check if the input is a URL
    if urlparse(input).scheme:
        return [input]
    # Check if the input is a file
    if os.path.isfile(input):
        with open(input, 'r') as f:
            return f.read().splitlines()
    print("Invalid input provided. Please provide a valid URL or a file containing a list of URLs.")
    return []

def save_result_html(new_endpoints: dict[str, list[str]],latest_endpoints_file: str, output_path : str, hostname: str) -> None:
    diff = diff_endpoints(read_endpoints_from_file(latest_endpoints_file), new_endpoints)
    # If there are no new endpoints, return early
    if diff == {}:
        return
    # Read the HTML template file
    if not os.path.exists(output_path):
        with open("result-template.html", 'r') as f:
            html_content = f.read().replace("$HOSTNAME$", hostname)
            with open(output_path, 'w') as f2:
                f2.write(html_content)
            # Don't add endpoints if the file was just created since were are monitoring for new endpoints
            return
    else:
        with open(output_path, 'r') as f:
            html_content = f.read()
    
    # Add the new endpoints to the HTML content
    for category, endpoints in diff.items():
        # Create a new HTML block for the new endpoints
        html_new_endpoints = f"<div class='endpoints-box'><h3>{category} - {date.today()}</h3>"
        for endpoint in endpoints:
            html_new_endpoints += f"<p>{endpoint}</p>"
        html_new_endpoints += "</div>"

    html_content = html_content.replace("<!-- $CONTENT$ -->", f"<!-- $CONTENT$ -->\n{html_new_endpoints}")

    # Write the updated HTML content to the output file
    with open(output_path, 'w') as f:
        f.write(html_content)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input",
                        help="Input a: URL to extract endpoints from or a file containing a list of URLs",
                        required="True")
    parser.add_argument("-H", "--headers", help="Headers to include in requests (e.g., 'User-Agent: Mozilla/5.0 ; CSRF-Token: TOKEN')", default="")
    parser.add_argument("-c", "--cookies", help="Cookies to include in requests (e.g, 'cookie1=aaaaaa; cookie2=bbbbbbbb')", default="")
    parser.add_argument("-o", "--output", help="Output directory to save the found endpoints", default="endpoints-output/")
    parser.add_argument("-w", "--discord-webhook", help="Discord webhook URL to notify about new endpoints", default="")
    parser.add_argument("-f", "--filter", help="Filter out common file extensions (e.g., .png, .jpg, .json, .svg)", action="store_true")


    args = parser.parse_args()

    # Remove trailing slash from the URL
    if args.input[-1:] == "/":
        args.input = args.input[:-1]
    

    # Convert headers and cookies to a dictionary
    headers = dict(x.split(': ') for x in args.headers.split(';')) if args.headers else {}
    cookies = dict(x.split('=', 1) for x in args.cookies.split(';') if '=' in x) if args.cookies else {}
    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    latest_endpoints_dir = os.path.join(args.output, "latest_endpoints")
    os.makedirs(latest_endpoints_dir, exist_ok=True)

    urls = get_urls_from_input(args.input)
    # Monitor endpoints for each URL
    for url in urls:
        # Extract JavaScript files from the URL
        js_files = extract_js_files(url, headers, cookies)

        # Extract endpoints from each JavaScript file
        endpoints = {}
        for js_file in js_files:
            js_content = get_file_content(js_file, headers, cookies)
            filename = urlparse(js_file).path
            endpoints[filename] = extract_endpoints_from_js(js_content, args.filter)

        hostname = urlparse(url).hostname
        latest_endpoints_file = os.path.join(latest_endpoints_dir, f"{hostname.replace(".", "-")}.txt")
        # Save new endpoints to the results file
        save_result_html(endpoints, latest_endpoints_file, os.path.join(args.output, f"result-{hostname.replace(".", "-")}.html"), hostname)
        # Notify about new endpoints using Discord webhook if provided
        if args.discord_webhook and os.path.exists(latest_endpoints_file):
            notify_discord_webhook(args.discord_webhook, endpoints, latest_endpoints_file, hostname)
        # Update latest endpoints file
        write_endpoints_to_file(endpoints, latest_endpoints_file)


