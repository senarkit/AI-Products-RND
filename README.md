# DeepDomainHarvester

DeepDomainHarvester is an asynchronous, recursive web crawler (spider) designed to extract large datasets (up to 20,000 records) on any specific topic. 

Unlike simple scrapers that rely solely on search engine APIs (which easily get rate-limited), DeepDomainHarvester seeds itself with search results and dynamic fallback URLs, and then **recursively crawls** the web by extracting and following `<a href>` links that match your topical keywords. 

Extracted data is automatically streamed to a timestamped CSV file in the `Output/` directory.

## Features

- **Asynchronous Crawling:** Utilizes `asyncio` and `aiohttp` with a concurrent worker pool (default 20 workers) for fast extraction.
- **Dynamic Fallbacks:** Automatically generates Wikipedia and GitHub search queries based on your topic to ensure the crawler always has starting seeds, even if search engine APIs fail.
- **Topical Keyword Filtering:** Prevents the crawler from wandering off-topic by verifying that newly discovered links contain topic-relevant keywords before adding them to the queue.
- **Auto-Streaming CSV:** Results are safely written to disk as they are extracted, preventing data loss in long-running jobs.

## Installation

Ensure you have Python 3.8+ installed. 

Install the required dependencies:
```bash
pip install aiohttp aiofiles beautifulsoup4 ddgs pydantic
```
*(Note: If you run into issues with the ddgs package, ensure you have the latest version `pip install --upgrade ddgs`)*

## Usage

You can launch the harvester from your terminal. By default, the script targets "FIFA World Cup 2026 win predictions".

### Basic Usage

To run the harvester on a custom topic, use the `--topic` argument. The script will automatically derive filtering keywords by splitting your topic into words.

```bash
python harvester.py --topic "SpaceX Mars colonization plans"
```

### Advanced Keyword Filtering

If you want strict control over which links the crawler follows, explicitly provide a comma-separated list of keywords using the `--keywords` argument. Only links containing at least one of these keywords will be queued.

```bash
python harvester.py --topic "Apple Vision Pro reviews" --keywords "apple,vision,headset,review,AR,VR"
```

### Test Mode (Dry Run)

If you just want to verify the output format or test the crawler's ability to find links without waiting for 20,000 records, append the `--test` flag. This limits the extraction to a maximum of 50 records.

```bash
python harvester.py --topic "Quantum computing advancements" --test
```

## How It Works

1. **Seeding**: The script attempts to find initial URLs via DuckDuckGo search. If rate-limited, it falls back to a dynamically constructed Wikipedia search URL based on your topic.
2. **Fetching & Parsing**: Workers asynchronously fetch the HTML and use BeautifulSoup to extract the page title, publisher, and main text content.
3. **Link Discovery**: All absolute and relative `<a href>` links are extracted. If a link matches your keywords, it gets added to the back of the queue.
4. **Validation & Output**: If the extracted text has a high enough confidence score (based on keyword density), it is saved as a `HarvesterRecord` directly to the CSV in `Output/`.
5. **Termination**: The worker pool gracefully shuts down the moment the 20,000 record limit is reached.
