import codecs
import re

with codecs.open('backend/kapt_scraper.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Replace the scraping loop
old_loop = """                    # Extract bid_no from onclick or href if possible, or just click it
                    links = await row.locator("a").all()
                    if not links:
                        continue
                        
                    main_link = links[0]
                    # 새 탭(팝업)으로 상세정보 열기
                    async with context.expect_page() as new_page_info:
                        await main_link.click()
                    detail_page = await new_page_info.value
                    
                    await detail_page.wait_for_load_state("networkidle")"""

new_loop = """                    # K-apt 리스트의 첫번째 td onclick 속성에서 bidNum 추출
                    td_onclick = await row.locator("td").first.get_attribute("onclick")
                    if not td_onclick or "goView" not in td_onclick:
                        continue
                        
                    match = re.search(r"goView\('(\d+)'\)", td_onclick)
                    if not match:
                        continue
                        
                    bid_num = match.group(1)
                    
                    # 새 탭으로 상세페이지 URL 직접 이동
                    detail_page = await context.new_page()
                    detail_url = f"https://www.k-apt.go.kr/bid/bidDetail.do?bidNum={bid_num}"
                    await detail_page.goto(detail_url, wait_until="networkidle")"""

text = text.replace(old_loop, new_loop)

with codecs.open('backend/kapt_scraper.py', 'w', encoding='utf-8') as f:
    f.write(text)