import asyncio
import traceback
import re
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context()
        page = await context.new_page()
        results = []
        try:
            print('Navigating...')
            await page.goto('https://www.k-apt.go.kr/bid/bidList.do', wait_until='networkidle', timeout=15000)
            await page.wait_for_selector('table tbody tr', timeout=10000)
            rows = await page.locator('table tbody tr').all()
            print(f'Count: {len(rows)}')
            
            for row in rows[:2]:
                try:
                    text_content = await row.inner_text()
                    if not text_content.strip() or '데이터가 없습니다' in text_content:
                        print('No data')
                        continue
                        
                    td_onclick = await row.locator('td').first.get_attribute('onclick')
                    print('onclick:', td_onclick)
                    if not td_onclick or 'goView' not in td_onclick:
                        print('No goView')
                        continue
                        
                    match = re.search(r"goView\('(\d+)'\)", td_onclick)
                    if not match:
                        print('No match')
                        continue
                        
                    bid_num = match.group(1)
                    print('bid_num:', bid_num)
                    
                    detail_page = await context.new_page()
                    detail_url = f'https://www.k-apt.go.kr/bid/bidDetail.do?bidNum={bid_num}'
                    print('detail:', detail_url)
                    await detail_page.goto(detail_url, wait_until='networkidle')
                    detail_text = await detail_page.evaluate('document.body.innerText')
                    print('Loaded detail:', detail_text[:100])
                    results.append(bid_num)
                    await detail_page.close()
                except Exception as e:
                    print('Row error:', traceback.format_exc())
                    
        except Exception as e:
            print('Error:', traceback.format_exc())
        finally:
            await browser.close()
            print('Final scraped count:', len(results))

if __name__ == '__main__':
    asyncio.run(test())