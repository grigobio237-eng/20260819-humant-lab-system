import asyncio
import re
import os
import sys
import datetime
import httpx
from playwright.async_api import async_playwright
from dynamic_parser import parse_bid_text

D2B_API_KEY = os.getenv("D2B_API_KEY", "06729b226c522143633d5b32cb343affcb4b20bc8b9c96627f9c109a65e7ab96")
# 실제 확인된 국방부 입찰공고 API 엔드포인트로 변경 필요
D2B_API_URL = os.getenv("D2B_API_URL", "http://apis.data.go.kr/1690000/DefenseProcurementService/getNoticeList")

async def fetch_d2b_bids_api(limit: int = 10, include_services: bool = False):
    """
    OpenAPI를 호출하여 기본 메타데이터(공고번호, 기초금액 등)를 경량 수집합니다.
    """
    params = {
        "ServiceKey": D2B_API_KEY,
        "numOfRows": limit,
        "pageNo": 1,
        "type": "json"
    }
    
    results = []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(D2B_API_URL, params=params, timeout=15.0)
            if response.status_code == 200:
                data = response.json()
                items = data.get("response", {}).get("body", {}).get("items", [])
                
                for item in items[:limit]:
                    # 시설공사만 수집 (include_services 가 False일 경우)
                    task_type = item.get("업무구분", "시설")
                    if not include_services and "용역" in task_type:
                        continue
                        
                    results.append({
                        "bid_no": item.get("공고번호", f"D2B-{datetime.datetime.now().strftime('%Y%m%d%H%M')}"),
                        "bid_name": item.get("공고명", "국방전자조달 입찰공고"),
                        "client_name": item.get("발주기관", "방위사업청"),
                        "base_price": float(item.get("기초금액", 0)),
                        "deadline": item.get("마감일시", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                    })
    except Exception as e:
        print(f"D2B API fetch error: {e}")
        
    # 만약 API가 아직 동작하지 않는 환경이라면, 테스트용 임시 데이터를 반환합니다.
    if not results:
        results.append({
            "bid_no": f"D2B-{datetime.datetime.now().strftime('%Y%m%d%H%M')}",
            "bid_name": "국방전자조달 테스트 시설공고",
            "client_name": "방위사업청",
            "base_price": 100000000.0,
            "deadline": (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
        })
        
    return results

async def scrape_d2b_details(bid_no: str):
    """
    Playwright를 사용하여 D2B 사이트에 접근하고 첨부파일 및 사정률 등을 파싱합니다.
    """
    url = "https://www.d2b.go.kr/index.do"
    
    result = {
        "region_condition": "",
        "license_condition": "",
        "extracted_a_value": 0.0,
        "extracted_lower_rate": 0.0,
        "a_value_breakdown": {},
        "confidence_level": "LOW",
        "range_min": 97.0,
        "range_max": 103.0,
    }
    
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
        
        # 봇 탐지 우회 (Stealth)
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        try:
            # 1. 메인 페이지 이동
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 2. iframe 핸들링
            main_frame = page.frame_locator("iframe#mainFrame").first
            
            # 3. 팝업 핸들링
            try:
                async with page.expect_popup(timeout=30000) as popup_info:
                    # 실제 환경에서는 UI를 클릭하거나 D2B의 특정 JS 함수를 호출해야 합니다.
                    # 여기서는 예시 URL을 팝업으로 엽니다.
                    await page.evaluate(f"window.open('https://www.d2b.go.kr/pz/wb/mo/openDetail.do?bid_no={bid_no}', '_blank', 'width=800,height=600')")
                
                popup = await popup_info.value
                await popup.wait_for_load_state("domcontentloaded")
                
                detail_text = await popup.evaluate("document.body.innerText")
                
                # 사정률 범위 파싱 (±2%, ±3%, 또는 98~102%)
                range_match = re.search(r"사정률\s*.*?(\d{1,2}(?:\.\d+)?)\s*~\s*(\d{1,3}(?:\.\d+)?)", detail_text)
                if range_match:
                    result["range_min"] = float(range_match.group(1))
                    result["range_max"] = float(range_match.group(2))
                else:
                    pm_match = re.search(r"±\s*(\d{1,2}(?:\.\d+)?)%", detail_text)
                    if pm_match:
                        val = float(pm_match.group(1))
                        result["range_min"] = 100.0 - val
                        result["range_max"] = 100.0 + val
                        
                # 첨부파일 분석
                parsed_data = parse_bid_text(detail_text, 0.0)
                result["extracted_a_value"] = parsed_data["extracted_a_value"]
                result["extracted_lower_rate"] = parsed_data["extracted_lower_rate"]
                result["a_value_breakdown"] = parsed_data["a_value_breakdown"]
                result["confidence_level"] = parsed_data["confidence_level"]
                
                # 첨부파일 다운로드
                attachment_dir = f"storage/attachments/D2B-{bid_no}"
                os.makedirs(attachment_dir, exist_ok=True)
                
                download_links = await popup.locator("a:has-text('다운로드'), a:has-text('공고문'), a[href*='download']").locator("visible=true").all()
                if download_links:
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
                
            except Exception as e:
                print(f"Popup extraction failed for {bid_no}: {e}")
                
        except Exception as e:
            print(f"D2B Scraper Error for {bid_no}: {e}")
        finally:
            await browser.close()
            
    return result

async def sync_d2b_bids(limit: int = 10, include_services: bool = False):
    """
    API 조회와 Playwright 상세 조회를 결합하는 메인 로직.
    """
    bids_meta = await fetch_d2b_bids_api(limit, include_services)
    
    results = []
    for meta in bids_meta:
        details = await scrape_d2b_details(meta["bid_no"])
        
        merged = {**meta, **details}
        merged["bid_full_no"] = f"D2B-{meta['bid_no']}"
        merged["client_name"] = f"[D2B] {meta['client_name']}"
        results.append(merged)
        
    return results
