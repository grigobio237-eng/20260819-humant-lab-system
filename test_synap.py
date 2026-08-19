from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
url = 'https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo=R26BK01684393&bidPbancOrd=000'

try:
    driver.get(url)
    time.sleep(5)
    
    # Try finding elements containing 미리보기
    previews = driver.find_elements(By.XPATH, "//*[contains(text(), '미리보기')]")
    print('Preview buttons:', len(previews))
    
    if previews:
        previews[0].click()
        time.sleep(3)
        
        handles = driver.window_handles
        driver.switch_to.window(handles[-1])
        print('Switched to preview window. URL:', driver.current_url)
        time.sleep(10)
        
        frames = driver.find_elements(By.TAG_NAME, 'iframe')
        print('Frames found:', len(frames))
        
        text = driver.execute_script('return document.body.innerText')
        print('Preview text length:', len(text))
        print(text[:200])
        print('-----')
        if '낙찰하한율' in text or '국민연금' in text:
            print('Found keywords!')
        else:
            print('Keywords NOT found!')
finally:
    driver.quit()