import re
with open('scratch/d2b_facility.html', 'r', encoding='utf-8') as f:
    html = f.read()
print('a.fgirdB matches:', len(re.findall(r'class=[\'"]fgirdB[\'"]', html)))
print('tr[id^=SBHE] matches:', len(re.findall(r'<tr[^>]+id=[\'"]SBHE', html)))
print('tr[id^=datagrid] matches:', len(re.findall(r'<tr[^>]+id=[\'"]datagrid', html)))
print('tr class matches:', set(re.findall(r'<tr[^>]+class=[\'"]([^\'"]+)[\'"]', html)))
