# Endpoints-Monitor

A tool designed to help bug bounty hunters monitor JavaScript files for new or updated endpoints. It scans for changes in JS files across bug bounty programs, helping you stay up-to-date with new features.

## Features

-   **Automated Endpoint Extraction**: Extracts potential API endpoints and URLs from JavaScript files.
-   **HTML Report Generation**: Generates an HTML report summarizing the new endpoints discovered, making it easy to review findings.
-   **Notification via Discord**: Sends real-time notifications to a Discord channel when a new endpoint is discovered.

## Installation

To use this tool, you need Python 3.x installed on your machine.

1. Clone the repository:
    ```bash
    git clone https://github.com/dd060606/Endpoints-Monitor.git
    cd Endpoints-Monitor
    python setup.py install
    ```
2. Install any required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

| Short Form | Long Form         | Description                                                                          |
| ---------- | ----------------- | ------------------------------------------------------------------------------------ |
| -i         | --input           | Input a: URL to extract endpoints from or a file containing a list of URLs           |
| -o         | --output          | Output directory to save the found endpoints                                         |
| -H         | --headers         | Headers to include in requests (e.g., 'User-Agent: Mozilla/5.0 ; CSRF-Token: TOKEN') |
| -c         | --cookies         | Cookies to include in requests (e.g, 'cookie1=aaaaaa; cookie2=bbbbbbbb')             |
| -w         | --discord-webhook | Discord webhook URL to notify about new endpoints                                    |
| -f         | --filter          | Filter out common file extensions (e.g., .png, .jpg, .json, .svg)                    |
| -h         | --help            | Show the help message and exit                                                       |

### Examples

`python endpoints-monitor.py -i https://example.com -f`

`python endpoints-monitor.py -i urls.txt -f`

`python endpoints-monitor.py -i urls.txt -w https://discord.com/api/webhooks/{...} -f`

`python endpoints-monitor.py -i urls.txt -w https://discord.com/api/webhooks/{...} -f -H 'User-Agent: BugBounty' -c 'token=aaaaa; cookie2=test'`
