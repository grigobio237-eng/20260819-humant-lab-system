import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("https://www.d2b.go.kr/peb/bid/announceList.do?key=41", wait_until="networkidle")
        await page.wait_for_selector("a.fgirdB", state="attached")
        
        print("Clicking link...")
        async with page.expect_navigation(timeout=10000):
            await page.locator("a.fgirdB").first.click(force=True)
        
        print("Navigated! URL:", page.url)
        
        await page.go_back(wait_until="networkidle")
        print("Gone back! URL:", page.url)
        
        await browser.close()

asyncio.run(run())
