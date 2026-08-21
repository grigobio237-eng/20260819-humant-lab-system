import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = await context.new_page()
        print("Navigating to d2b...")
        await page.goto("https://www.d2b.go.kr/index.do", wait_until="networkidle")
        
        # Check frames
        print(f"Frames count: {len(page.frames)}")
        
        # We need to find the link to "국내조달 -> 입찰공고" or similar
        html = await page.content()
        with open("scratch/d2b_main.html", "w", encoding="utf-8") as f:
            f.write(html)
            
        print("Done. Saved to scratch/d2b_main.html")
        await browser.close()

asyncio.run(run())
