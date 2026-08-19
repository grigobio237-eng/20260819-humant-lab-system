import re
import asyncio
import os
import shutil
from playwright.async_api import async_playwright
from dynamic_parser import parse_bid_text

async def scrape_g2b_details(bid_no: str, bid_seq: str, bid_full_no: str, base_price: float = 0.0):
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
        
        result = {
            "region_condition": "",
            "license_condition": "",
            "extracted_a_value": 0.0,
            "extracted_lower_rate": 0.0,
            "a_value_breakdown": {},
            "confidence_level": "LOW",
            "status": "error"
        }
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
            text = await page.evaluate("document.body.innerText")
            
            # 1. 지역/면허 추출
            region_match = re.search(r"참가가능지역\s*\[(.*?)\]", text)
            if region_match:
                result["region_condition"] = region_match.group(1).strip()
            else:
                region_match2 = re.search(r"지역제한.*?\[(.*?)\]", text, re.DOTALL)
                if region_match2:
                    result["region_condition"] = region_match2.group(1).strip()
            
            license_matches = re.findall(r"\[([^\]]*?\d{4})\]", text)
            if not license_matches:
                license_matches = re.findall(r"\[([^\]]*?업)\]", text)
                
            if license_matches:
                unique_licenses = list(dict.fromkeys(license_matches))
                result["license_condition"] = ", ".join(unique_licenses)
                
            # 2. 첨부파일 다운로드 및 미리보기 추출
            # 나라장터 첨부파일 영역의 <a> 태그나 버튼을 찾습니다.
            attachment_dir = f"storage/attachments/{bid_full_no}"
            os.makedirs(attachment_dir, exist_ok=True)
            
            # 본문 내의 "안내서", "공고문" 링크 찾기 로직 (간소화)
            # 여기서는 모든 미리보기 버튼 중 하나를 클릭한다고 가정
            preview_buttons = await page.locator("text='미리보기'").all()
            if preview_buttons:
                for btn in preview_buttons:
                    try:
                        async with context.expect_page() as new_page_info:
                            await btn.click(timeout=5000)
                        preview_page = await new_page_info.value
                        
                        # Synap Viewer 로딩 대기
                        await preview_page.wait_for_selector("body", state="visible", timeout=15000)
                        # Synap의 텍스트가 모두 렌더링되기를 기다림 (클래스나 특정 태그가 없으면 단순히 sleep)
                        await asyncio.sleep(2) 
                        
                        preview_text = await preview_page.evaluate("document.body.innerText")
                        
                        parsed_data = parse_bid_text(preview_text, base_price)
                        if parsed_data["confidence_level"] in ["HIGH", "MEDIUM"]:
                            result["extracted_a_value"] = parsed_data["extracted_a_value"]
                            result["extracted_lower_rate"] = parsed_data["extracted_lower_rate"]
                            result["a_value_breakdown"] = parsed_data["a_value_breakdown"]
                            result["confidence_level"] = parsed_data["confidence_level"]
                            break
                        
                        await preview_page.close()
                    except Exception as e:
                        print("Preview parsing error:", e)
            
            # 다운로드 파일 (공고문 등) - 백그라운드 저장
            try:
                # '공고'나 '안내서'가 포함된 링크 다운로드
                download_links = await page.locator("a:has-text('공고'), a:has-text('안내서')").all()
                if download_links:
                    try:
                        async with page.expect_download(timeout=5000) as download_info:
                            await download_links[0].click(timeout=5000)
                        download = await download_info.value
                        await download.save_as(os.path.join(attachment_dir, download.suggested_filename))
                    except Exception as e:
                        print(f"Download error: {e}")
            except Exception as e:
                print("Download error:", e)
                
            result["status"] = "success"
            return result
            
        except Exception as e:
            print(f"[Scraper Error] {bid_full_no}: {e}")
            return result
        finally:
            await browser.close()
