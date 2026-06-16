import asyncio
import aiohttp
import aiofiles
import csv
import json
import argparse
import datetime
import os
import re
import urllib.parse
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from pydantic import BaseModel, Field
from typing import Optional, List, Tuple

# Pydantic Schema for Validation
class HarvesterRecord(BaseModel):
    parent_topic: str
    source_url: str
    page_title: str
    publisher_or_author: str
    language: str = "en"
    extracted_at: str
    data_format: str
    information_category: str
    extracted_content: str
    has_media: bool
    http_status: int
    confidence_score: float

class DeepDomainHarvester:
    def __init__(self, topic: str, max_records: int = 20000, max_concurrent: int = 20):
        self.topic = topic
        self.max_records = max_records
        self.max_concurrent = max_concurrent
        self.seen_urls = set()
        self.extracted_count = 0
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(script_dir, "Output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_csv = os.path.join(self.output_dir, f"harvester_results_{timestamp}.csv")
        self.fieldnames = list(HarvesterRecord.model_fields.keys())
        
        # Topical keywords for link filtering
        self.keywords = ["prediction", "world cup", "2026", "win", "odds", "fifa", "soccer", "football", "match"]
        
        self.queue = asyncio.Queue()
        
        # Initialize CSV with headers
        with open(self.output_csv, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            writer.writeheader()

    def get_discovery_urls(self, query: str, limit: int = 50):
        print(f"[*] Discovering URLs for query: {query}")
        urls = []
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=limit)
                for r in results:
                    urls.append(r.get('href'))
        except Exception as e:
            print(f"[!] DuckDuckGo Search failed: {e}")
            
        # Always append robust fallback URLs to ensure starting points
        print(f"[*] Adding fallback seed URLs...")
        fallbacks = [
            "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup",
            "https://www.sportingnews.com/us/soccer/news/fifa-world-cup-2026-odds-predictions-favorites/m9vq8t2xz2d71h2xj1f6i9a",
            "https://www.goal.com/en-us/lists/world-cup-2026-power-rankings/bltaf9c0e5a8f9c1b7f",
            "https://www.foxsports.com/soccer/2026-fifa-world-cup",
            "https://www.espn.com/soccer/"
        ]
        urls.extend(fallbacks)
        return list(set(urls))

    async def fetch_page(self, session: aiohttp.ClientSession, url: str):
        try:
            async with session.get(url, timeout=15, ssl=False) as response:
                status = response.status
                # only process html
                if 'text/html' not in response.headers.get('Content-Type', ''):
                    return url, status, ""
                html = await response.text()
                return url, status, html
        except Exception as e:
            # Silence specific fetch errors to avoid spamming the console
            return url, 0, ""

    def parse_page(self, url: str, status: int, html: str) -> Tuple[Optional[HarvesterRecord], List[str]]:
        if status != 200 or not html:
            return None, []
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract new links
        new_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Convert to absolute URL
            absolute_url = urllib.parse.urljoin(url, href)
            # Basic sanitization
            absolute_url = absolute_url.split('#')[0]
            if absolute_url.startswith('http'):
                new_links.append(absolute_url)
        
        # Extract fields for record
        page_title = soup.title.string.strip() if soup.title and soup.title.string else "Unknown Title"
        
        publisher = "Unknown Publisher"
        meta_author = soup.find("meta", {"name": "author"})
        if meta_author:
            publisher = meta_author.get("content", publisher)
            
        has_media = bool(soup.find("img") or soup.find("video"))
        
        paragraphs = soup.find_all('p')
        text_content = "\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
        if not text_content:
            return None, new_links
            
        extracted_content = text_content[:1500] + "..." if len(text_content) > 1500 else text_content
        
        match_count = sum(1 for kw in self.keywords if kw.lower() in text_content.lower())
        confidence = min(0.5 + (match_count * 0.1), 1.0)
        
        record = None
        try:
            record = HarvesterRecord(
                parent_topic=self.topic,
                source_url=url,
                page_title=page_title[:200],
                publisher_or_author=publisher[:100],
                language="en",
                extracted_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                data_format="text_paragraph",
                information_category="win_predictions",
                extracted_content=extracted_content,
                has_media=has_media,
                http_status=status,
                confidence_score=round(confidence, 2)
            )
        except Exception as e:
            pass
            
        return record, new_links

    async def stream_to_csv(self, record: HarvesterRecord):
        async with aiofiles.open(self.output_csv, mode='a', newline='', encoding='utf-8') as f:
            import io
            sio = io.StringIO()
            w = csv.DictWriter(sio, fieldnames=self.fieldnames)
            w.writerow(record.model_dump())
            await f.write(sio.getvalue())

    def is_topic_relevant(self, url: str) -> bool:
        # Check if URL looks like it might contain our keywords to avoid crawling everything
        url_lower = url.lower()
        # Fast filter on URLs
        for kw in self.keywords:
            if kw.replace(' ', '') in url_lower or kw.replace(' ', '-') in url_lower:
                return True
        return False

    async def worker(self, worker_id: int, session: aiohttp.ClientSession):
        while self.extracted_count < self.max_records:
            try:
                # Use a timeout so workers can exit if the queue is temporarily empty but might get filled,
                # though here we might just break if the queue is truly dead.
                url = await asyncio.wait_for(self.queue.get(), timeout=10.0)
            except asyncio.TimeoutError:
                # Queue empty for a while, exit worker
                break
                
            if self.extracted_count >= self.max_records:
                self.queue.task_done()
                break

            url, status, html = await self.fetch_page(session, url)
            if status == 200 and html:
                record, new_links = self.parse_page(url, status, html)
                
                # Add new links to queue
                for link in new_links:
                    if link not in self.seen_urls:
                        self.seen_urls.add(link)
                        # To prevent queue explosion and stay on topic
                        if self.is_topic_relevant(link):
                            self.queue.put_nowait(link)
                
                if record and record.confidence_score > 0.6:
                    await self.stream_to_csv(record)
                    self.extracted_count += 1
                    if self.extracted_count % 10 == 0:
                        print(f"[Worker-{worker_id}] Extracted ({self.extracted_count}/{self.max_records}) from {url}")

            self.queue.task_done()

    async def run(self):
        print(f"[*] Starting DeepDomainHarvester for topic: '{self.topic}'")
        print(f"[*] Target records: {self.max_records}")
        print(f"[*] Output file: {self.output_csv}")
        
        # Initial Seeds
        seed_urls = self.get_discovery_urls(self.topic, limit=100)
        for url in seed_urls:
            if url not in self.seen_urls:
                self.seen_urls.add(url)
                self.queue.put_nowait(url)
                
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 DeepDomainHarvester/1.0'}
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Create worker tasks
            workers = [asyncio.create_task(self.worker(i, session)) for i in range(self.max_concurrent)]
            
            # Wait until queue is fully processed or we hit max_records
            # Instead of queue.join(), we can just wait for workers to finish
            # since workers will exit when max_records is hit or queue is empty for 10s.
            await asyncio.gather(*workers)
            
        print(f"[*] Harvester finished. Total records: {self.extracted_count}")
        print(f"[*] Results saved to: {self.output_csv}")

    async def process_local_file(self, filepath: str, original_url: str):
        print(f"[*] Processing local file (Agent-Assisted Mode): {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        record, _ = self.parse_page(original_url, 200, content)
        if record and record.confidence_score >= 0.0:
            await self.stream_to_csv(record)
            self.extracted_count += 1
            print(f"[+] Extracted ({self.extracted_count}/{self.max_records}) from {original_url}")
        else:
            print("[!] Validation failed or confidence too low.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DeepDomainHarvester Scraper")
    parser.add_argument("--test", action="store_true", help="Run in test mode (max 50 records)")
    parser.add_argument("--local", type=str, help="Path to local file fetched by agent")
    parser.add_argument("--url", type=str, help="Original URL for the local file")
    args = parser.parse_args()
    
    topic = "FIFA World Cup 2026 win predictions"
    max_rec = 50 if args.test else 20000
    
    harvester = DeepDomainHarvester(topic, max_records=max_rec)
    
    if args.local and args.url:
        asyncio.run(harvester.process_local_file(args.local, args.url))
        print(f"[*] Harvester finished. Total records: {harvester.extracted_count}")
        print(f"[*] Results saved to: {harvester.output_csv}")
    else:
        try:
            asyncio.run(harvester.run())
        except KeyboardInterrupt:
            print("[*] Interrupted by user.")
