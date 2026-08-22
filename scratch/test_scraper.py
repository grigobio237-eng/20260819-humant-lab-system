import asyncio
import sys
import os
sys.path.insert(0, os.path.abspath('backend'))
from d2b_scraper import scrape_d2b_bids

async def main():
    bids = await scrape_d2b_bids(3)
    with open('scratch/test_3.log', 'w', encoding='utf-8') as f:
        f.write(f'Found {len(bids)} bids\n')
        for b in bids:
            f.write(f'{b["bid_no"]} - A_value: {b.get("extracted_a_value", 0)}\n')

asyncio.run(main())
