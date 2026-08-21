import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        page.on("request", lambda request: print(">>", request.method, request.url))
        
        await page.goto("https://www.d2b.go.kr/peb/bid/announceList.do?key=41", wait_until="networkidle")
        await page.wait_for_selector("a.fgirdB", state="attached")
        
        print("Clicking link...")
        await page.locator("a.fgirdB").first.click(force=True)
        
        await page.wait_for_timeout(3000)
        
        await browser.close()

asyncio.run(run())
