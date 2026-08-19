import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        detail_page = await context.new_page()
        print("Loading list page...")
        await detail_page.goto('https://www.k-apt.go.kr/bid/bidList.do', wait_until='domcontentloaded')
        print("Executing goView('20260819200537978')...")
        
        async with detail_page.expect_navigation(wait_until="domcontentloaded"):
            await detail_page.evaluate("goView('20260819200537978')")
            
        text = await detail_page.evaluate("document.body.innerText")
        print("Extracted text:")
        print(text)
        await browser.close()

asyncio.run(test())
