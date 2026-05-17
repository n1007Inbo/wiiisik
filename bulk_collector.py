"""
Pinterest Bulk URL Collector
============================
Reads profiles from 'profiles.txt' and collects all Pin URLs for each.
Saves results into the 'collected_urls' folder.
"""

import asyncio
import csv
import os
import sys
import time
import random
from playwright.async_api import async_playwright

# Config
SCROLL_DELAY = (2.0, 4.0)
MAX_STALL = 15
HEADLESS = True

async def collect_profile_urls(browser, profile_url, output_folder):
    # Create filename from profile URL
    profile_name = profile_url.strip('/').split('/')[-1]
    output_file = os.path.join(output_folder, f"{profile_name}_urls.csv")
    
    print(f"\n  🔍 Starting Profile: {profile_url}")
    
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    urls = set()
    
    try:
        await page.goto(profile_url, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(5)
        
        stall = 0
        scrolls = 0
        
        while scrolls < 5000: # Safety cap
            links = await page.query_selector_all('a[href*="/pin/"]')
            new_found = 0
            for link in links:
                href = await link.get_attribute("href")
                if href:
                    clean = href.split('?')[0].split('#')[0]
                    if clean.startswith('/'): clean = "https://www.pinterest.com" + clean
                    if "/pin/" in clean and clean not in urls:
                        urls.add(clean)
                        new_found += 1
            
            if new_found > 0:
                stall = 0
                sys.stdout.write(f"\r  📌 Found: {len(urls):>5} | Scrolls: {scrolls:>4}")
                sys.stdout.flush()
            else:
                stall += 1
                if stall >= MAX_STALL: break
                if stall % 3 == 0:
                    await page.evaluate("window.scrollBy(0, -800)")
                    await asyncio.sleep(1)
            
            await page.evaluate(f"window.scrollBy(0, {random.randint(800, 1200)})")
            await asyncio.sleep(random.uniform(*SCROLL_DELAY))
            scrolls += 1
            
        # Save to CSV
        if urls:
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['url'])
                for u in sorted(list(urls)): writer.writerow([u])
            print(f"\n  ✅ Saved {len(urls)} URLs to {output_file}")
        else:
            print(f"\n  ⚠️ No URLs found for {profile_url}")
            
    except Exception as e:
        print(f"\n  ❌ Error on {profile_url}: {e}")
    finally:
        await context.close()

async def main():
    input_file = "profiles.txt"
    output_dir = "collected_urls"
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_file):
        print(f"  ❌ Error: {input_file} not found! Create it and add Pinterest profile URLs (one per line).")
        return
        
    with open(input_file, 'r') as f:
        profiles = [line.strip() for line in f if line.strip().startswith('http')]
        
    if not profiles:
        print("  ⚠️ No valid profile URLs found in profiles.txt")
        return
        
    print(f"🚀 Starting Bulk Collection for {len(profiles)} profiles...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        for profile in profiles:
            await collect_profile_urls(browser, profile, output_dir)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
