import codecs

content = """import asyncio
import re
import os
import datetime
from playwright.async_api import async_playwright
from dynamic_parser import parse_bid_text

async def scrape_kapt_bids(limit: int = 10):
    url = "https://www.k-apt.go.kr/bid/bidList.do"
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.wait_for_selector("table tbody tr", timeout=10000)
            await asyncio.sleep(2)
            
            rows = await page.locator("table tbody tr").all()
            
            for row in rows[:limit]:
                try:
                    text_content = await row.inner_text()
                    if not text_content.strip() or "데이터가 없습니다" in text_content:
                        continue
                        
                    td_onclick = await row.locator("td").first.get_attribute("onclick")
                    if not td_onclick or "goView" not in td_onclick:
                        continue
                        
                    match = re.search(r"goView\('([A-Za-z0-9\-]+)'\)", td_onclick)
                    if not match:
                        continue
                        
                    bid_num = match.group(1)
                    
                    detail_page = await context.new_page()
                    detail_url = f"https://www.k-apt.go.kr/bid/bidDetail.do?bidNum={bid_num}"
                    await detail_page.goto(detail_url, wait_until="networkidle")
                    detail_text = await detail_page.evaluate("document.body.innerText")
                    
                    bid_no_match = re.search(r"공고번호\s*[:\]]?\s*([A-Za-z0-9\-]+)", detail_text)
                    bid_name_match = re.search(r"입찰공고명\s*[:\]]?\s*(.+)", detail_text)
                    client_match = re.search(r"단지명\s*[:\]]?\s*(.+)", detail_text)
                    base_price_match = re.search(r"기초금액\s*[:\]]?\s*금?\s*([\d,]+)\s*원", detail_text)
                    deadline_match = re.search(r"서류제출\s*마감일시\s*[:\]]?\s*([\d\-\.\s:]+)", detail_text)
                    
                    bid_no = bid_no_match.group(1).strip() if bid_no_match else f"KAPT-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                    bid_name = bid_name_match.group(1).strip() if bid_name_match else "K-apt 민간공고"
                    client_name = client_match.group(1).strip() if client_match else "아파트단지"
                    base_price = float(base_price_match.group(1).replace(",", "")) if base_price_match else 0.0
                    deadline_str = deadline_match.group(1).strip() if deadline_match else datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    region_cond = ""
                    license_cond = ""
                    region_match = re.search(r"지역제한\s*[:\]]?\s*(.+)", detail_text)
                    if region_match: region_cond = region_match.group(1).strip()
                    
                    license_match = re.search(r"참가자격\s*[:\]]?\s*(.+)", detail_text)
                    if license_match: license_cond = license_match.group(1).strip()
                    
                    attachment_dir = f"storage/attachments/{bid_no}"
                    os.makedirs(attachment_dir, exist_ok=True)
                    
                    download_links = await detail_page.locator("a:has-text('다운로드'), a:has-text('공고문'), a:has-text('파일')").all()
                    if download_links:
                        try:
                            async with detail_page.expect_download(timeout=5000) as download_info:
                                await download_links[0].click()
                            download = await download_info.value
                            await download.save_as(os.path.join(attachment_dir, download.suggested_filename))
                        except:
                            pass
                    
                    parsed_data = parse_bid_text(detail_text, base_price)
                    
                    results.append({
                        "bid_full_no": bid_no,
                        "bid_no": bid_no,
                        "bid_seq": "000",
                        "bid_name": bid_name,
                        "client_name": f"[K-apt] {client_name}",
                        "base_price": base_price,
                        "region_condition": region_cond,
                        "license_condition": license_cond,
                        "deadline": deadline_str,
                        "extracted_a_value": parsed_data["extracted_a_value"],
                        "extracted_lower_rate": parsed_data["extracted_lower_rate"],
                        "a_value_breakdown": parsed_data["a_value_breakdown"],
                        "confidence_level": parsed_data["confidence_level"]
                    })
                    
                    await detail_page.close()
                except Exception as e:
                    print(f"K-apt row parsing error: {e}")
                    
        except Exception as e:
            print(f"K-apt Scraper Error: {e}")
        finally:
            await browser.close()
            
    return results
"""
with codecs.open('backend/kapt_scraper.py', 'w', encoding='utf-8') as f:
    f.write(content)
