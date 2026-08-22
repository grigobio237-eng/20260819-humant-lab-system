import asyncio
import re
import os
import sys
import datetime
from playwright.async_api import async_playwright
from dynamic_parser import parse_bid_text

async def scrape_d2b_bids(limit: int = 10, include_services: bool = False):
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox', 
                '--disable-setuid-sandbox', 
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        
        main_page = await context.new_page()
        
        try:
            print("D2B 시설공고 목록 페이지 접속 중...")
            await main_page.goto("https://www.d2b.go.kr/peb/bid/announceList.do?key=41", wait_until="networkidle", timeout=30000)
            
            await main_page.wait_for_selector("a.fgirdB", state="attached", timeout=15000)
            await main_page.wait_for_timeout(2000)
            
            rows = await main_page.locator("tr:has(a.fgirdB)").all()
            
            if not rows:
                print("D2B 공고 목록을 찾을 수 없습니다.")
                return results
                
            processed = 0
            
            # 파싱할 아이템들의 메타데이터를 먼저 모두 수집합니다.
            items_to_process = []
            
            for row in rows:
                if len(items_to_process) >= limit:
                    break
                    
                try:
                    tds = await row.locator("td").all()
                    if len(tds) < 10:
                        continue
                        
                    bid_no_text = await tds[2].inner_text()
                    bid_no_match = re.search(r"(\d{4}-\d{5,})", bid_no_text)
                    if not bid_no_match:
                        continue
                    bid_no = bid_no_match.group(1)
                    
                    bid_name = await tds[4].inner_text()
                    client_name = await tds[5].inner_text()
                    
                    deadline_text = await tds[7].inner_text()
                    deadline_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", deadline_text)
                    deadline = deadline_match.group(1) + ":00" if deadline_match else (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    price_text = await tds[9].inner_text()
                    base_price = float(re.sub(r"[^\d.]", "", price_text)) if re.sub(r"[^\d.]", "", price_text) else 0.0
                    
                    if base_price == 0:
                        continue
                        
                    # 중복 공고 방지 (SBGrid에 동일 공고가 여러 번 렌더링되는 경우)
                    if any(item["bid_no"] == bid_no for item in items_to_process):
                        processed += 1
                        continue
                        
                    items_to_process.append({
                        "index": processed, # row index for clicking
                        "bid_no": bid_no,
                        "bid_name": bid_name.strip(),
                        "client_name": client_name.strip(),
                        "deadline": deadline,
                        "base_price": base_price
                    })
                    processed += 1
                except Exception as e:
                    print(f"메타데이터 추출 중 오류: {e}")
                    
            await main_page.close()
            
            # 이제 각 항목별로 새 탭을 열어서 상세 정보를 파싱합니다.
            for item in items_to_process:
                detail_result = {
                    "region_condition": "",
                    "license_condition": "",
                    "extracted_a_value": 0.0,
                    "extracted_lower_rate": 0.0,
                    "a_value_breakdown": {},
                    "confidence_level": "LOW",
                    "range_min": 97.0,
                    "range_max": 103.0,
                }
                
                detail_page = await context.new_page()
                try:
                    await detail_page.goto("https://www.d2b.go.kr/peb/bid/announceList.do?key=41", wait_until="networkidle", timeout=15000)
                    await detail_page.wait_for_selector("a.fgirdB", state="attached", timeout=10000)
                    await detail_page.wait_for_timeout(1000)
                    
                    # 해당 인덱스의 링크 클릭 및 네비게이션 대기
                    async with detail_page.expect_navigation(timeout=10000):
                        await detail_page.locator("a.fgirdB").nth(item["index"]).click(force=True)
                        
                    await detail_page.wait_for_load_state("domcontentloaded")
                    await detail_page.wait_for_timeout(1000)
                    
                    detail_text = await detail_page.evaluate("document.body.innerText")
                    
                    # 사정률 및 A값 파싱
                    range_match = re.search(r"사정률\s*.*?(\d{1,2}(?:\.\d+)?)\s*~\s*(\d{1,3}(?:\.\d+)?)", detail_text)
                    if range_match:
                        detail_result["range_min"] = float(range_match.group(1))
                        detail_result["range_max"] = float(range_match.group(2))
                    else:
                        pm_match = re.search(r"±\s*(\d{1,2}(?:\.\d+)?)%", detail_text)
                        if pm_match:
                            val = float(pm_match.group(1))
                            detail_result["range_min"] = 100.0 - val
                            detail_result["range_max"] = 100.0 + val
                            
                    parsed_data = parse_bid_text(detail_text, item["base_price"])
                    detail_result.update(parsed_data)
                    
                    # 첨부파일 다운로드
                    attachment_dir = f"storage/attachments/D2B-{item['bid_no']}"
                    os.makedirs(attachment_dir, exist_ok=True)
                    
                    download_links = await detail_page.locator("a:has-text('다운로드'), a:has-text('공고문'), a[href*='download']").locator("visible=true").all()
                    for d_link in download_links:
                        try:
                            async with detail_page.expect_download(timeout=5000) as download_info:
                                await d_link.click(timeout=5000, force=True)
                            download = await download_info.value
                            await download.save_as(os.path.join(attachment_dir, download.suggested_filename))
                            break
                        except Exception as e:
                            print(f"[D2B Download Error] {item['bid_no']}: {e}")
                            
                except Exception as ex:
                    print(f"[{item['bid_no']}] 상세 페이지 파싱 실패: {ex}")
                finally:
                    await detail_page.close()
                    
                results.append({
                    "bid_full_no": f"D2B-{item['bid_no']}",
                    "bid_no": item["bid_no"],
                    "bid_name": item["bid_name"],
                    "client_name": item["client_name"],
                    "base_price": item["base_price"],
                    "deadline": item["deadline"],
                    **detail_result
                })
                    
        except Exception as e:
            print(f"D2B Scraper Main Error: {e}")
            raise e
        finally:
            await browser.close()
            
    return results
