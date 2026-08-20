with open('backend/main.py', 'a', encoding='utf-8') as f:
    f.write('''

from d2b_scraper import sync_d2b_bids

@app.get("/api/v1/d2b/sync")
def sync_d2b_bids_api(limit: int = 10, include_services: bool = False, db: Session = Depends(get_db)):
    import asyncio
    d2b_bids = asyncio.run(sync_d2b_bids(limit, include_services))
    saved_count = 0
    
    for b in d2b_bids:
        existing = db.query(models.Bid).filter(models.Bid.bid_full_no == b["bid_full_no"]).first()
        if not existing:
            dynamic_lower_rate = b.get("extracted_lower_rate") if b.get("extracted_lower_rate") > 0 else get_lower_rate(b["base_price"], b["client_name"])
            recommended_est_rate = get_recommended_est_rate([], b.get("range_min", 97.0), b.get("range_max", 103.0), b["client_name"])
            
            calculated_price, net_cost_applied = calculate_bid_price(
                base_price=b["base_price"],
                est_rate=recommended_est_rate,
                a_value=b.get("extracted_a_value", 0.0),
                lower_rate=dynamic_lower_rate
            )
            
            new_bid = models.Bid(
                bid_full_no=b["bid_full_no"],
                bid_no=b["bid_no"],
                bid_seq=b.get("bid_seq", "00"),
                bid_name=b["bid_name"],
                client_name=b["client_name"],
                region_code="",
                license_condition=b.get("license_condition", ""),
                region_condition=b.get("region_condition", ""),
                raw_data=b,
                base_price=b["base_price"],
                a_value=b.get("extracted_a_value", 0.0),
                net_cost=0.0,
                lower_rate=dynamic_lower_rate,
                range_min=b.get("range_min", 97.0),
                range_max=b.get("range_max", 103.0),
                deadline=datetime.datetime.strptime(b["deadline"], "%Y-%m-%d %H:%M:%S") if isinstance(b["deadline"], str) else b["deadline"],
                link_url=f"https://www.d2b.go.kr/pz/wb/mo/openDetail.do?bid_no={b['bid_no']}",
                status="OPEN"
            )
            db.add(new_bid)
            
            new_calc = models.CalculatedBid(
                bid_full_no=new_bid.bid_full_no,
                recommended_est_rate=recommended_est_rate,
                calculated_bid_price=calculated_price,
                is_net_cost_applied=net_cost_applied,
                review_status="PENDING"
            )
            db.add(new_calc)
            saved_count += 1
            
    db.commit()
    return {"status": "success", "scraped": len(d2b_bids), "saved": saved_count}
''')
