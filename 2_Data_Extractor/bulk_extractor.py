"""
Pinterest Bulk Data Extractor
=============================
Reads all CSV files from 'inputs' folder and extracts detailed data.
Saves results into the 'outputs' folder.
Supports Resume: Skips already processed URLs across all files.
"""

import asyncio
import csv
import json
import os
import sys
import time
import random
from datetime import datetime
from playwright.async_api import async_playwright

# Config
CONCURRENT = 4
RETRIES = 3
HEADLESS = True

CSV_FIELDS = [
    "pin_id", "pin_url", "title", "description", "destination_url", 
    "image_url", "board_name", "author_name", "author_followers", 
    "tags", "saves_count", "comment_count", "created_date", "scraped_at"
]

JS_EXTRACT = r"""
() => {
    const d = { 
        title: "N/A", description: "N/A", destination_url: "N/A", 
        image_url: "N/A", board_name: "N/A", author_name: "N/A",
        author_followers: "N/A", tags: [], saves_count: "0", 
        comment_count: "0", created_date: "N/A" 
    };
    try {
        const body = document.body.innerHTML;
        const h1 = document.querySelector('h1');
        if (h1) d.title = h1.innerText.trim();
        const ogImg = document.querySelector('meta[property="og:image"]');
        if (ogImg) d.image_url = ogImg.content;
        const scriptData = Array.from(document.querySelectorAll('script[type="application/json"]'))
            .find(s => s.innerHTML.includes('closeup_unified_description') || s.innerHTML.includes('aggregated_pin_data'));
        if (scriptData) {
            const raw = scriptData.innerHTML;
            const descMatch = raw.match(/"closeup_unified_description":"([^"]+)"/);
            if (descMatch) d.description = descMatch[1];
            const savesMatch = raw.match(/"repin_count":(\d+)/) || raw.match(/"saves":(\d+)/);
            if (savesMatch) d.saves_count = savesMatch[1];
            const commMatch = raw.match(/"comment_count":(\d+)/);
            if (commMatch) d.comment_count = commMatch[1];
            const boardMatch = raw.match(/"board":\{"name":"([^"]+)"/);
            if (boardMatch) d.board_name = boardMatch[1];
            const authorMatch = raw.match(/"owner":\{"full_name":"([^"]+)"/);
            if (authorMatch) d.author_name = authorMatch[1];
            const followMatch = raw.match(/"follower_count":(\d+)/);
            if (followMatch) d.author_followers = followMatch[1];
            const dateMatch = raw.match(/"created_at":"([^"]+)"/);
            if (dateMatch) d.created_date = dateMatch[1];
        }
        const tags = Array.from(document.querySelectorAll('a[href*="/search/pins/"]'))
            .map(a => a.innerText.replace('#', '').trim())
            .filter(t => t.length > 0);
        d.tags = [...new Set(tags)].join(', ');
    } catch (e) {}
    return d;
}
"""

class BulkExtractor:
    def __init__(self):
        self.processed = set()
        self.lock = asyncio.Lock()
        self.stats = {"done": 0, "total": 0, "errors": 0}

    def load_processed(self, output_dir):
        if not os.path.exists(output_dir): return
        for f in os.listdir(output_dir):
            if f.endswith('.csv'):
                try:
                    with open(os.path.join(output_dir, f), 'r', encoding='utf-8-sig') as file:
                        reader = csv.DictReader(file)
                        for row in reader: self.processed.add(row['pin_url'])
                except: pass

    async def process_pin(self, browser, url, output_file, semaphore):
        async with semaphore:
            pin_id = url.split('/pin/')[-1].strip('/')
            for attempt in range(1, RETRIES + 1):
                context = None
                try:
                    context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")
                    page = await context.new_page()
                    await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2}", lambda r: r.abort())
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await asyncio.sleep(2)
                    data = await page.evaluate(JS_EXTRACT)
                    
                    row = {
                        "pin_id": pin_id, "pin_url": url, "title": data["title"],
                        "description": data["description"], "destination_url": data["destination_url"],
                        "image_url": data["image_url"], "board_name": data["board_name"],
                        "author_name": data["author_name"], "author_followers": data["author_followers"],
                        "tags": data["tags"], "saves_count": data["saves_count"],
                        "comment_count": data["comment_count"], "created_date": data["created_date"],
                        "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    async with self.lock:
                        file_exists = os.path.isfile(output_file)
                        with open(output_file, 'a', newline='', encoding='utf-8-sig') as f:
                            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                            if not file_exists: writer.writeheader()
                            writer.writerow(row)
                        self.stats["done"] += 1
                        pct = (self.stats["done"] / self.stats["total"] * 100)
                        sys.stdout.write(f"\r  📊 Progress: {pct:.1f}% ({self.stats['done']}/{self.stats['total']}) | Errors: {self.stats['errors']}")
                        sys.stdout.flush()
                    return
                except:
                    if attempt == RETRIES: self.stats["errors"] += 1
                    else: await asyncio.sleep(2)
                finally:
                    if context: await context.close()

    async def run(self):
        input_dir = "inputs"
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        self.load_processed(output_dir)
        
        if not os.path.exists(input_dir):
            print(f"  ❌ Error: {input_dir} folder not found!")
            return
            
        csv_files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
        if not csv_files:
            print("  ⚠️ No CSV files found in 'inputs' folder.")
            return
            
        print(f"🚀 Starting Bulk Extraction for {len(csv_files)} files...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=HEADLESS)
            semaphore = asyncio.Semaphore(CONCURRENT)
            
            for csv_file in csv_files:
                input_path = os.path.join(input_dir, csv_file)
                output_path = os.path.join(output_dir, f"data_{csv_file}")
                
                with open(input_path, 'r') as f:
                    urls = [row['url'] for row in csv.DictReader(f) if row.get('url')]
                
                todo = [u for u in urls if u not in self.processed]
                if not todo: continue
                
                self.stats["total"] += len(todo)
                print(f"\n  📂 Processing: {csv_file} ({len(todo)} new pins)")
                
                tasks = [self.process_pin(browser, url, output_path, semaphore) for url in todo]
                await asyncio.gather(*tasks)
                
            await browser.close()
        print(f"\n\n✅ DONE! All data saved in '{output_dir}' folder.")

if __name__ == "__main__":
    extractor = BulkExtractor()
    asyncio.run(extractor.run())
