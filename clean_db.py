from backend.database import SessionLocal
from backend.models import Bid, CalculatedBid

db = SessionLocal()
bad_bids = db.query(Bid).filter(Bid.bid_name == "K-apt 민간공고").all()
for b in bad_bids:
    db.query(CalculatedBid).filter(CalculatedBid.bid_full_no == b.bid_full_no).delete()
    db.delete(b)
db.commit()
print(f"Deleted {len(bad_bids)} bad bids.")
