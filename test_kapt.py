import asyncio
from playwright.async_api import async_playwright
import json

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def handle_response(response):
            if "json" in response.headers.get("content-type", "") or "ajax" in response.url.lower():
                try:
                    body = await response.text()
                    if "bid" in body or "list" in body:
                        print(f"API Found: {response.url}")
                        print(body[:200])
                except:
                    pass
                    
        page.on("response", handle_response)
        
        await page.goto("https://www.k-apt.go.kr/bid/bidList.do")
        await asyncio.sleep(5)
        
        # Click search button just in case
        try:
            await page.click("#btnSearch")
            await asyncio.sleep(5)
        except:
            pass
            
        await browser.close()

asyncio.run(run())