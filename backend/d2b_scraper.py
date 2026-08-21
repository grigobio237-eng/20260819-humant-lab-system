import asyncio
import re
import os
import sys
import datetime
from playwright.async_api import async_playwright
from dynamic_parser import parse_bid_text

async def scrape_d2b_bids(limit: int = 10, include_services: bool = False):
    """
    1안 (Pure Playwright): 공공데이터 API 없이 D2B 웹사이트(시설공고)에서 목록과 상세를 모두 스크래핑.
    """
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
        
        page = await context.new_page()
        
        try:
            print("D2B 시설공고 목록 페이지 접속 중...")
            await page.goto("https://www.d2b.go.kr/peb/bid/announceList.do?key=41", wait_until="networkidle", timeout=30000)
            
            # 목록 테이블(SBGrid)이 로딩될 때까지 대기
            await page.wait_for_selector("a.fgirdB", state="visible", timeout=15000)
            await page.wait_for_timeout(2000) # SBGrid 렌더링 안정화
            
            # 테이블 행(tr) 목록 가져오기
            # SBGrid는 보통 <tr class="sbgrid_datagrid_DataRow"> 등의 형태를 띕니다.
            rows = await page.locator("tr[id^='SBHE_datagrid']").all()
            
            if not rows:
                print("D2B 공고 목록을 찾을 수 없습니다.")
                return results
                
            processed = 0
            for row in rows:
                if processed >= limit:
                    break
                    
                try:
                    # SBGrid 컬럼별 데이터 추출
                    tds = await row.locator("td").all()
                    if len(tds) < 10:
                        continue
                        
                    # 공고번호 (2번 텍스트 안에 있음, e.g. 2026-08-18 2026-12541)
                    bid_no_text = await tds[2].inner_text()
                    bid_no_match = re.search(r"(\d{4}-\d{5,})", bid_no_text)
                    if not bid_no_match:
                        continue
                    bid_no = bid_no_match.group(1)
                    
                    # 공고명
                    bid_name = await tds[4].inner_text()
                    bid_name = bid_name.strip()
                    
                    # 발주기관
                    client_name = await tds[5].inner_text()
                    client_name = client_name.strip()
                    
                    # 마감일시 (7번 텍스트 안에 있음, e.g. 2026-08-24 10:00\n2026-08-24 10:30)
                    deadline_text = await tds[7].inner_text()
                    deadline_match = re.search(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", deadline_text)
                    deadline = deadline_match.group(1) + ":00" if deadline_match else (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
                    
                    # 기초예가 (9번 텍스트, e.g. 22,566,000 원)
                    price_text = await tds[9].inner_text()
                    base_price = float(re.sub(r"[^\d.]", "", price_text)) if re.sub(r"[^\d.]", "", price_text) else 0.0
                    
                    if base_price == 0:
                        continue # 기초금액 없는 공고는 제외
                        
                    # 상세 팝업 열기 (공고명 링크 클릭)
                    link_element = tds[4].locator("a")
                    
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
                    
                    try:
                        async with page.expect_popup(timeout=10000) as popup_info:
                            await link_element.click()
                        
                        popup = await popup_info.value
                        await popup.wait_for_load_state("domcontentloaded")
                        await popup.wait_for_timeout(1000)
                        
                        detail_text = await popup.evaluate("document.body.innerText")
                        
                        # 사정률 파싱
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
                                
                        parsed_data = parse_bid_text(detail_text, base_price)
                        detail_result["extracted_a_value"] = parsed_data["extracted_a_value"]
                        detail_result["extracted_lower_rate"] = parsed_data["extracted_lower_rate"]
                        detail_result["a_value_breakdown"] = parsed_data["a_value_breakdown"]
                        detail_result["confidence_level"] = parsed_data["confidence_level"]
                        
                        # 첨부파일 다운로드
                        attachment_dir = f"storage/attachments/D2B-{bid_no}"
                        os.makedirs(attachment_dir, exist_ok=True)
                        
                        download_links = await popup.locator("a:has-text('다운로드'), a:has-text('공고문'), a[href*='download']").locator("visible=true").all()
                        for d_link in download_links:
                            try:
                                async with popup.expect_download(timeout=5000) as download_info:
                                    await d_link.click(timeout=5000)
                                download = await download_info.value
                                await download.save_as(os.path.join(attachment_dir, download.suggested_filename))
                                break
                            except:
                                pass
                                
                        await popup.close()
                    except Exception as ex:
                        print(f"[{bid_no}] 상세 팝업 처리 실패: {ex}")
                    
                    results.append({
                        "bid_full_no": f"D2B-{bid_no}",
                        "bid_no": bid_no,
                        "bid_name": bid_name,
                        "client_name": client_name,
                        "base_price": base_price,
                        "deadline": deadline,
                        **detail_result
                    })
                    processed += 1
                    
                except Exception as e:
                    print(f"행 처리 중 오류 발생: {e}")
                    continue
                    
        except Exception as e:
            print(f"D2B Scraper Main Error: {e}")
        finally:
            await browser.close()
            
    return results
