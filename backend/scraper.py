import re
import asyncio

async def scrape_g2b_details(bid_no: str, bid_seq: str):
    from playwright.async_api import async_playwright
    
    # R로 시작하면 차세대 시스템, 숫자로 시작하면 구 시스템
    if bid_no.startswith('R'):
        url = f"https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo={bid_no}&bidPbancOrd={bid_seq}"
    else:
        url = f"https://www.g2b.go.kr/pt/menu/selectSubFrame.do?framesrc=/ep/invitation/publish/bidInfoDtl.do?bidno={bid_no}%26bidseq={bid_seq}"
        
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            # 15초 타임아웃, 네트워크 안정화 대기
            await page.goto(url, wait_until="networkidle", timeout=15000)
            
            # 페이지에 렌더링된 모든 텍스트 추출
            text = await page.evaluate("document.body.innerText")
            
            region_cond = ""
            license_cond = ""
            
            # 1. 참가가능지역 추출 (예: 참가가능지역 [경기도])
            region_match = re.search(r"참가가능지역\s*\[(.*?)\]", text)
            if region_match:
                region_cond = region_match.group(1).strip()
            else:
                # 차세대시스템 외의 패턴 대비
                region_match2 = re.search(r"지역제한.*?\[(.*?)\]", text, re.DOTALL)
                if region_match2:
                    region_cond = region_match2.group(1).strip()
            
            # 2. 업종제한 추출 (예: [기계설비·가스공사업(6202)] 업종을 등록한 업체)
            # 보통 괄호 안에 업종코드 4자리가 있거나 '업'으로 끝나는 패턴을 찾음
            license_matches = re.findall(r"\[([^\]]*?\d{4})\]", text)
            if not license_matches:
                license_matches = re.findall(r"\[([^\]]*?업)\]", text)
                
            if license_matches:
                # 중복 제거 후 합치기
                unique_licenses = list(dict.fromkeys(license_matches))
                license_cond = ", ".join(unique_licenses)
                
            return {
                "region_condition": region_cond,
                "license_condition": license_cond,
                "status": "success"
            }
            
        except Exception as e:
            print(f"[Scraper Error] {bid_no}: {e}")
            return {
                "region_condition": "",
                "license_condition": "",
                "status": "error"
            }
        finally:
            await browser.close()
