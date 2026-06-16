---
name: deep-domain-harvester
description: An autonomous data harvesting skill designed to execute deep, multi-threaded extraction loops on a given topic until a minimum threshold of 20,000 unique structured records is successfully populated into the target schema.
---

# Agent Skill Specification: DeepDomainHarvester

## Core Objective
An autonomous data harvesting skill designed to execute deep, multi-threaded extraction loops on a given topic to populate a CSV dataset with up to 20,000 unique structured records.

### Implementation Architecture (Agent-Assisted Local Parsing)
Because the native OS/terminal sandbox lacks direct DNS resolution (`getaddrinfo` fails silently for Python HTTP requests), automated scripts cannot natively fetch external websites like Wikipedia or DuckDuckGo in this specific environment.

**The Solution:** The execution of this skill MUST use a hybrid **Agent-Assisted** approach:
1. The Agent uses its internal native tool (`read_url_content`) to fetch the target URLs directly, bypassing the terminal's DNS limitations.
2. The Agent saves the web content to its internal markdown path.
3. The Agent executes the `harvester.py` script locally, passing the local file path using the newly added `--local` flag and `--url` flag.

Example Agent Command:
```powershell
python harvester.py --local "C:\path\to\agent\content.md" --url "https://en.wikipedia.org/..."
```

### 1. Skill Execution Loop (Hybrid Logic)
1. **Discovery Loop:** Use DuckDuckGo Search API to seed URL discovery.
2. **Throttled Extraction Loop:** Concurrently fetch and parse pages using `aiohttp` and `BeautifulSoup4`. 
3. **Data Streaming:** Stream validated Pydantic JSON records directly to a CSV file appended with the current datetime inside an `Output/` directory relative to the script path. 

### 2. Termination Criteria
- **Stop Condition:** `total_validated_records` >= 20000 or search results exhausted.

### 3. Data Schema Definitions (Strict CSV Output)
Every row in the CSV output must conform to this schema:
- `parent_topic` (String)
- `source_url` (String)
- `page_title` (String)
- `publisher_or_author` (String)
- `language` (String)
- `extracted_at` (String)
- `data_format` (Enum): `[text_paragraph, table_data, bullet_list, dynamic_card]`
- `information_category` (String)
- `extracted_content` (String | Object)
- `has_media` (Boolean)
- `http_status` (Integer)
- `confidence_score` (Float)
