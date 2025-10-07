# GitHub Crawler

A simple asynchronous crawler for searching GitHub repositories, issues, or wikis by keywords.
Built with **Python 3.10+**, **aiohttp**, and **BeautifulSoup4**.

---

## Features

* Search GitHub by keywords (Repositories, Issues, or Wikis).
* Support for proxies (with or without authentication).
* Fetch additional information about repositories:

  * Repository owner
  * Programming languages usage statistics
* Configurable via JSON input file.

---

## Installation

Clone the repository:

```bash
git clone https://github.com/zvarych-oleksii/githubcrawler.git
cd githubcrawler
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Linux / MacOS
.venv\Scripts\activate      # Windows (PowerShell)
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Configuration

Copy `.env-template` to `.env` and configure:

```env
REQUEST_TIMEOUT=10
```

Prepare an input JSON file (`input_data.json`):

```json
{
  "keywords": ["python", "django-rest-framework", "jwt"],
  "proxies": ["ip:port"],
  "type": "Repositories",
  "extra": true
}
```

* **keywords** — list of keywords to search.
* **proxies** — list of proxies (both `ip:port` and `user:pass@ip:port` are supported).
* **type** — search type: `Repositories`, `Issues`, or `Wikis`.
* **extra** — if `true`, fetch repository owner and language stats.

---

## Usage

Run the crawler:

```bash
python main.py
```

Example output:

```json
[
  {
    "url": "https://github.com/owner/repo",
    "extra": {
      "owner": "owner",
      "language_stats": {
        "Python": 85.0,
        "C++": 15.0
      }
    }
  }
]
```

---

## Running Tests

The project uses **pytest**:

```bash
pytest
```

---

## Project Structure

```
github-crawler/
├── crawler/
│   ├── __init__.py
│   ├── base.py
│   └── github.py
├── tests/
│   ├── __init__.py
│   └── test_github.py
├── .env-template
├── .gitignore
├── config.py
├── input_data.json
├── main.py
├── requirements.txt
└── README.md
```

---

