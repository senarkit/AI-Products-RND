<p align="center">
  <img src="https://img.shields.io/badge/python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+"/>
  <img src="https://img.shields.io/badge/async-aiohttp-2C5BB4?style=for-the-badge&logo=aiohttp&logoColor=white" alt="aiohttp"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/badge/parser-BeautifulSoup4-43B02A?style=for-the-badge" alt="BeautifulSoup4"/>
  <img src="https://img.shields.io/badge/search-DuckDuckGo-DE5833?style=for-the-badge&logo=duckduckgo&logoColor=white" alt="DuckDuckGo"/>
</p>

<h1 align="center">🕸️ DeepDomainHarvester</h1>

<p align="center">
  <strong>An asynchronous, recursive web crawler built to extract large-scale topical datasets from the open web.</strong>
</p>

<p align="center">
  Seed it with a topic &rarr; it discovers, crawls, filters, and streams up to <b>20,000 high-relevance records</b> straight into a timestamped CSV.
</p>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [CLI Reference](#-cli-reference)
- [How It Works](#-how-it-works)
- [Output Schema](#-output-schema)
- [Data Quality](#-data-quality)
- [Project Structure](#-project-structure)
- [Configuration & Tuning](#-configuration--tuning)
- [Limitations & Caveats](#-limitations--caveats)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔍 Overview

Unlike simple scrapers that rely solely on search engine APIs (which easily get rate-limited), **DeepDomainHarvester** seeds itself with search results _and_ dynamic fallback URLs, then **recursively crawls** the web by extracting and following `<a href>` links that match your topical keywords.

Every extracted page is validated with a keyword-density confidence score, structured through a [Pydantic](https://docs.pydantic.dev/) schema, and **streamed in real-time** to a timestamped CSV — so even if a long-running job is interrupted, you never lose data.

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| **⚡ Async Worker Pool** | `asyncio` + `aiohttp` with 20 concurrent workers by default — thousands of pages per minute. |
| **🌱 Smart Seeding** | Seeds via DuckDuckGo search. If rate-limited, automatically falls back to Wikipedia and GitHub search queries derived from your topic. |
| **🎯 Topical Link Filtering** | Prevents off-topic drift by checking every discovered URL against your keyword list before queuing it. |
| **📊 Confidence Scoring** | Each page gets a `0.5`–`1.0` confidence score based on keyword density; pages below `0.6` are discarded. |
| **💾 Real-Time CSV Streaming** | Results are appended to disk as they arrive via `aiofiles` — no data loss on interruption. |
| **✅ Pydantic Validation** | Every record is validated through a strict `HarvesterRecord` schema before being written. |
| **🧪 Test Mode** | `--test` flag caps extraction at 50 records for quick dry runs. |
| **📁 Agent-Assisted Mode** | `--local` flag lets you feed pre-fetched HTML files for parsing (useful for AI agent pipelines). |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   DeepDomainHarvester                    │
├──────────────────────────────────────────────────────────┤
│                                                          │
│   ┌─────────────┐     ┌──────────────────────────────┐   │
│   │  CLI / Args │────▶│   DeepDomainHarvester.__init__ │   │
│   └─────────────┘     └──────────┬───────────────────┘   │
│                                  │                       │
│                                  ▼                       │
│                     ┌────────────────────┐               │
│                     │  Seed Discovery    │               │
│                     │  (DuckDuckGo +     │               │
│                     │   Wikipedia/GitHub │               │
│                     │   Fallbacks)       │               │
│                     └────────┬───────────┘               │
│                              │                           │
│                              ▼                           │
│                     ┌────────────────────┐               │
│                     │   asyncio.Queue    │◀──────┐       │
│                     │   (URL Frontier)   │       │       │
│                     └────────┬───────────┘       │       │
│                              │                   │       │
│             ┌────────────────┼────────────────┐  │       │
│             ▼                ▼                ▼  │       │
│        ┌─────────┐    ┌─────────┐     ┌─────────┤       │
│        │Worker-0 │    │Worker-1 │ ... │Worker-N ││       │
│        │ fetch   │    │ fetch   │     │ fetch   ││       │
│        │ parse   │    │ parse   │     │ parse   ││       │
│        │ filter  │    │ filter  │     │ filter  ││       │
│        └────┬────┘    └────┬────┘     └────┬────┘│       │
│             │              │               │     │       │
│             │   new topic-relevant links ──────────┘       │
│             │              │               │             │
│             ▼              ▼               ▼             │
│        ┌─────────────────────────────────────────┐       │
│        │  Confidence Filter (score > 0.6)        │       │
│        └────────────────────┬────────────────────┘       │
│                             │                            │
│                             ▼                            │
│        ┌─────────────────────────────────────────┐       │
│        │  Pydantic Validation (HarvesterRecord)  │       │
│        └────────────────────┬────────────────────┘       │
│                             │                            │
│                             ▼                            │
│        ┌─────────────────────────────────────────┐       │
│        │  CSV Writer (aiofiles, append mode)     │       │
│        │  Output/harvester_results_TIMESTAMP.csv │       │
│        └─────────────────────────────────────────┘       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 📦 Installation

### Prerequisites

- **Python 3.8+** (tested on 3.10, 3.11, 3.12)
- `pip` or your preferred Python package manager

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/senarkit/AI-Products-RND.git
cd AI-Products-RND

# (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# Install dependencies
pip install aiohttp aiofiles beautifulsoup4 ddgs pydantic
```

> [!TIP]
> If you run into issues with the `ddgs` package, make sure you have the latest version:
> ```bash
> pip install --upgrade ddgs
> ```

---

## 🚀 Quick Start

### 1. Basic Run

Give it any topic and let the crawler do the rest:

```bash
python harvester.py --topic "SpaceX Mars colonization plans"
```

### 2. Custom Keywords

Lock down which links the crawler follows:

```bash
python harvester.py --topic "Apple Vision Pro reviews" --keywords "apple,vision,headset,review,AR,VR"
```

### 3. Test Mode (Dry Run)

Verify the output format without waiting for 20,000 records:

```bash
python harvester.py --topic "Quantum computing advancements" --test
```

### 4. Agent-Assisted Mode

Feed a pre-downloaded HTML file for parsing:

```bash
python harvester.py --topic "Climate change policy" --local page.html --url "https://example.com/article"
```

---

## 🖥️ CLI Reference

```
usage: harvester.py [-h] [--test] [--local LOCAL] [--url URL]
                    [--topic TOPIC] [--keywords KEYWORDS]
```

| Argument | Type | Default | Description |
| :--- | :---: | :--- | :--- |
| `--topic` | `str` | `"FIFA World Cup 2026 win predictions"` | The search topic to harvest data for. |
| `--keywords` | `str` | Auto-derived from topic | Comma-separated keywords for link filtering (e.g. `"win,odds,football"`). |
| `--test` | `flag` | `False` | Run in test mode — caps extraction at **50** records. |
| `--local` | `str` | — | Path to a locally saved HTML file to parse instead of crawling. |
| `--url` | `str` | — | The original URL for the `--local` file (used for record metadata). |

---

## ⚙️ How It Works

The harvester operates as a **5-stage pipeline**:

### Stage 1 — Seed Discovery

```
Topic → DuckDuckGo Search (up to 100 results)
                 ↓  (on failure)
         Wikipedia + GitHub fallback URLs
```

The system always appends dynamic fallback URLs regardless of search success, guaranteeing the crawler has starting points even when APIs are rate-limited.

### Stage 2 — Asynchronous Fetching

20 concurrent workers pull URLs from an `asyncio.Queue`. Each worker:
1. Fetches the page via `aiohttp` (15s timeout, SSL verification disabled for resilience)
2. Validates the response is `text/html`
3. Returns the raw HTML for parsing

### Stage 3 — Parsing & Link Discovery

Using **BeautifulSoup**, each page is parsed to extract:
- **Page title** from `<title>` tag
- **Author/publisher** from `<meta name="author">` tag
- **Text content** by concatenating substantial `<p>` tags (>50 chars each, truncated to 1,500 chars)
- **Media presence** by detecting `<img>` and `<video>` elements
- **All `<a href>` links**, resolved to absolute URLs and de-fragmented

### Stage 4 — Topical Filtering

Newly discovered links are checked against the keyword list:

```python
# A link is topic-relevant if any keyword appears in the URL
url_lower = url.lower()
for kw in self.keywords:
    if kw.replace(' ', '') in url_lower or kw.replace(' ', '-') in url_lower:
        return True
```

Only relevant links are added back to the queue, preventing the crawler from wandering off-topic.

### Stage 5 — Validation & Output

Each page receives a **confidence score** based on keyword density:

```
confidence = min(0.5 + (keyword_matches × 0.1), 1.0)
```

Records scoring **above 0.6** are validated through the Pydantic `HarvesterRecord` schema and streamed to the CSV file in real-time.

---

## 📋 Output Schema

All extracted data is stored in CSV format at `Output/harvester_results_YYYYMMDD_HHMMSS.csv` with the following columns:

| Column | Type | Description |
| :--- | :---: | :--- |
| `parent_topic` | `str` | The search topic that initiated the crawl. |
| `source_url` | `str` | The absolute URL of the crawled page. |
| `page_title` | `str` | The HTML `<title>` of the page (max 200 chars). |
| `publisher_or_author` | `str` | From `<meta name="author">`, defaults to `"Unknown Publisher"`. |
| `language` | `str` | Language code, currently defaults to `"en"`. |
| `extracted_at` | `str` | UTC ISO-8601 timestamp of when the page was crawled. |
| `data_format` | `str` | Format of extracted data, defaults to `"text_paragraph"`. |
| `information_category` | `str` | Broad categorization of the data (configurable in source). |
| `extracted_content` | `str` | Concatenated paragraph text, max 1,500 characters. |
| `has_media` | `bool` | `True` if the page contains `<img>` or `<video>` elements. |
| `http_status` | `int` | HTTP response status code (e.g., `200`). |
| `confidence_score` | `float` | `0.5`–`1.0` keyword-density relevance score. |

### Example Output

```csv
parent_topic,source_url,page_title,publisher_or_author,language,extracted_at,data_format,information_category,extracted_content,has_media,http_status,confidence_score
SpaceX Mars,https://example.com/article,Mars Colony Plans,Jane Doe,en,2026-06-17T01:30:00+00:00,text_paragraph,win_predictions,"SpaceX has announced plans for...",True,200,0.80
```

---

## 📈 Data Quality

The harvester employs **three layers of quality control** to ensure high-fidelity output:

| Layer | Mechanism | Effect |
| :--- | :--- | :--- |
| **URL Filtering** | Keyword matching in discovered URLs | Prevents off-topic pages from being fetched |
| **Content Filtering** | Minimum 50-char paragraph threshold | Removes navigation, footers, and boilerplate |
| **Confidence Gating** | Score > 0.6 required for output | Only keyword-dense, topically relevant pages are saved |

> [!NOTE]
> The resulting dataset will heavily skew toward dense, informative paragraphs directly related to your target topic rather than generic navigation text or off-topic articles.

---

## 📂 Project Structure

```
AI-Products-RND/
├── harvester.py          # Main crawler script (all logic in one file)
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── LICENSE               # MIT License
├── .gitignore            # Git ignore rules (includes *.csv)
├── Output/               # Auto-created directory for CSV results
│   └── harvester_results_YYYYMMDD_HHMMSS.csv
└── venv/                 # Virtual environment (not tracked)
```

---

## 🔧 Configuration & Tuning

The harvester's behavior can be adjusted by modifying constants in `harvester.py`:

| Parameter | Default | Location | Description |
| :--- | :---: | :--- | :--- |
| `max_records` | `20,000` | `__init__` | Maximum records to extract before stopping. |
| `max_concurrent` | `20` | `__init__` | Number of async worker coroutines. |
| Fetch timeout | `15s` | `fetch_page` | Per-page HTTP request timeout. |
| Content truncation | `1,500 chars` | `parse_page` | Max length of `extracted_content`. |
| Min paragraph length | `50 chars` | `parse_page` | Filters out short, non-informative `<p>` tags. |
| Confidence threshold | `> 0.6` | `worker` | Minimum score for a record to be saved. |
| Queue idle timeout | `10s` | `worker` | Workers exit if the queue is empty for this long. |
| Search seed limit | `100` | `run` | Max initial URLs from DuckDuckGo. |

> [!IMPORTANT]
> Increasing `max_concurrent` beyond 50 may cause target servers to block your IP or return rate-limit errors. Use responsibly.

---

## ⚠️ Limitations & Caveats

- **No JavaScript rendering** — Pages that load content dynamically via JavaScript (SPAs, React apps) will yield empty or minimal text.
- **English-only** — The `language` field is currently hardcoded to `"en"`. Non-English pages are still crawled but not language-detected.
- **`information_category` is static** — Defaults to `"win_predictions"` and must be manually changed in source for other use cases.
- **No robots.txt compliance** — The crawler does not check `robots.txt` before fetching pages. Use responsibly and respect website policies.
- **No deduplication of content** — URL-level deduplication is enforced, but two different URLs serving identical content will produce duplicate records.
- **SSL verification disabled** — `ssl=False` is used in `fetch_page` for resilience, which means the crawler will connect to servers with invalid certificates.

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License · Copyright (c) 2026 Arkit Sen
```

---

<p align="center">
  Built with ❤️ and <code>asyncio</code>
</p>
