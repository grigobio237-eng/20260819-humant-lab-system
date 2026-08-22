import sys
with open('backend/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

out = []
skip = False
for line in lines:
    if line.startswith('@app.get(\"/api/v1/bids/{bid_full_no}/download\")'):
        skip = True
        out.append('from fastapi.responses import RedirectResponse\n')
        out.append(line)
        out.append('def download_attachment(bid_full_no: str, db: Session = Depends(get_db)):\n')
        out.append('    bid = db.query(models.Bid).filter(models.Bid.bid_full_no == bid_full_no).first()\n')
        out.append('    if bid and bid.link_url:\n')
        out.append('        return RedirectResponse(url=bid.link_url)\n')
        out.append('    raise HTTPException(status_code=404, detail=\"File not found\")\n')
        continue
    if skip:
        if line.startswith('@app.get(\"/api/v1/bids\")'):
            skip = False
            out.append(line)
    else:
        out.append(line)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.writelines(out)
