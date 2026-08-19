import codecs

with codecs.open('backend/kapt_scraper.py', 'r', encoding='ansi') as f:
    text = f.read()

# Fix the broken text back to normal if possible
text = text.replace("?낆같怨듦퀬紐", "입찰공고명")
text = text.replace("?⑥?紐", "단지명")
text = text.replace("湲곗큹湲덉븸", "기초금액")
text = text.replace("?쒕쪟?쒖텧", "서류제출")
text = text.replace("留덇컧?쇱떆", "마감일시")
text = text.replace("吏€??젣??", "지역제한")
text = text.replace("李멸??먭꺽", "참가자격")
text = text.replace("?ㅼ슫濡쒕뱶", "다운로드")
text = text.replace("怨듦퀬臾", "공고문")

with codecs.open('backend/kapt_scraper.py', 'w', encoding='utf-8') as f:
    f.write(text)