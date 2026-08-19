from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import datetime

from engine import get_recommended_est_rate, calculate_bid_price, check_qualification, fetch_a_value, get_lower_rate
from database import engine, get_db
import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="휴먼트 랩 시스템 API",
    description="건설 입찰 공고 최적 투찰가 계산 및 적격심사 판별 백엔드 시스템입니다.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BidPayload(BaseModel):
    bid_full_no: str = Field(...)
    bid_no: str = Field(...)
    bid_seq: str = Field(...)
    bid_name: str = Field(...)
    client_name: str = Field(...)
    base_price: float = Field(...)
    a_value: float = Field(0.0)
    net_cost: float = Field(0.0)
    lower_rate: float = Field(...)
    range_min: float = Field(97.0)
    range_max: float = Field(103.0)
    deadline: datetime.datetime = Field(...)
    license_condition: Optional[str] = Field(None)
    region_condition: Optional[str] = Field(None)
    raw_data: Optional[dict] = Field(None)

class CompanyProfilePayload(BaseModel):
    company_name: str
    business_reg_no: str
    region_code: str
    licenses: Dict[str, float]
    
MOCK_PAST_RATES = []

@app.get("/")
def read_root():
    return {"status": "ok"}

# --- 회사 관리 API ---
@app.get("/api/v1/companies")
def get_companies(db: Session = Depends(get_db)):
    companies = db.query(models.CompanyProfile).order_by(models.CompanyProfile.id).all()
    return companies

@app.post("/api/v1/companies")
def create_company(payload: CompanyProfilePayload, db: Session = Depends(get_db)):
    new_company = models.CompanyProfile(
        company_name=payload.company_name,
        business_reg_no=payload.business_reg_no,
        region_code=payload.region_code,
        licenses=payload.licenses
    )
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company

@app.put("/api/v1/companies/{company_id}")
def update_company(company_id: int, payload: CompanyProfilePayload, db: Session = Depends(get_db)):
    company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    company.company_name = payload.company_name
    company.business_reg_no = payload.business_reg_no
    company.region_code = payload.region_code
    company.licenses = payload.licenses
    db.commit()
    db.refresh(company)
    return company

@app.delete("/api/v1/companies/{company_id}")
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    db.delete(company)
    db.commit()
    return {"status": "success"}

# --- 공고 API ---
@app.post("/api/v1/calculate")
def process_new_bid(payload: BidPayload, db: Session = Depends(get_db)):
    existing_bid = db.query(models.Bid).filter(models.Bid.bid_full_no == payload.bid_full_no).first()
    if existing_bid:
        return {"status": "skipped", "message": "이미 처리된 공고입니다."}

    import asyncio
    from scraper import scrape_g2b_details
    # 크롤러 실행 (동기 블록 안에서 asyncio.run 사용)
    scraped_data = asyncio.run(scrape_g2b_details(payload.bid_no, payload.bid_seq))
    
    if payload.raw_data is None:
        payload.raw_data = {}
        
    if scraped_data.get("status") == "success":
        # OpenAPI에서 비어있던 데이터를 크롤링 데이터로 덮어쓰기
        if scraped_data.get("license_condition"):
            payload.raw_data["prtcptQlfCndNm"] = scraped_data["license_condition"]
            payload.license_condition = scraped_data["license_condition"]
        if scraped_data.get("region_condition"):
            payload.raw_data["prtcptPosblRgnNm"] = scraped_data["region_condition"]
            payload.region_condition = scraped_data["region_condition"]

    fetched_a_value = fetch_a_value(payload.bid_no, payload.bid_seq)
    final_a_value = fetched_a_value if fetched_a_value > 0 else payload.a_value
    dynamic_lower_rate = get_lower_rate(payload.base_price, payload.client_name)
    recommended_est_rate = get_recommended_est_rate(MOCK_PAST_RATES, payload.range_min, payload.range_max, payload.client_name)
    calc_result = calculate_bid_price(
        payload.base_price, final_a_value, payload.net_cost, dynamic_lower_rate, recommended_est_rate
    )
    
    new_bid = models.Bid(
        bid_full_no=payload.bid_full_no,
        bid_no=payload.bid_no,
        bid_seq=payload.bid_seq,
        bid_name=payload.bid_name,
        client_name=payload.client_name,
        base_price=payload.base_price,
        a_value=final_a_value,
        net_cost=payload.net_cost,
        lower_rate=dynamic_lower_rate,
        range_min=payload.range_min,
        range_max=payload.range_max,
        deadline=payload.deadline,
        license_condition=payload.license_condition,
        region_condition=payload.region_condition,
        raw_data=payload.raw_data or {}
    )
    db.add(new_bid)
    
    new_calc = models.CalculatedBid(
        bid_full_no=payload.bid_full_no,
        is_qualified=False, # 동적 판별로 대체됨
        recommended_est_rate=recommended_est_rate,
        calculated_bid_price=calc_result["calculated_bid_price"],
        is_net_cost_applied=calc_result["is_net_cost_applied"]
    )
    db.add(new_calc)
    db.commit()
    
    return {"status": "success", "bid_full_no": payload.bid_full_no}

@app.get("/api/v1/bids")
def get_bids(company_id: Optional[int] = None, db: Session = Depends(get_db)):
    company = None
    if company_id:
        company = db.query(models.CompanyProfile).filter(models.CompanyProfile.id == company_id).first()
        
    results = db.query(models.Bid, models.CalculatedBid).outerjoin(
        models.CalculatedBid, models.Bid.bid_full_no == models.CalculatedBid.bid_full_no
    ).order_by(models.Bid.created_at.desc()).all()
    
    data = []
    for bid, calc in results:
        is_qualified = False
        if company:
            is_qualified = check_qualification(
                bid.license_condition or '',
                bid.region_condition or '',
                company.licenses or {},
                company.region_code or '',
                bid.bid_name or '',
                float(bid.base_price or 0)
            )
            
        data.append({
            "bid_full_no": bid.bid_full_no,
            "bid_name": bid.bid_name,
            "client_name": bid.client_name,
            "base_price": float(bid.base_price),
            "range": f"{bid.range_min}% ~ {bid.range_max}%",
            "recommended_est_rate": float(calc.recommended_est_rate) if calc else 0.0,
            "calculated_bid_price": float(calc.calculated_bid_price) if calc else 0.0,
            "is_qualified": is_qualified,
            "deadline": bid.deadline.strftime("%Y-%m-%d %H:%M"),
            "status": calc.review_status if calc else "PENDING",
            "a_value": float(bid.a_value),
            "net_cost": float(bid.net_cost),
            "lower_rate": float(bid.lower_rate),
            "is_net_cost_applied": calc.is_net_cost_applied if calc else False,
            "raw_data": bid.raw_data or {},
            "link_url": f"https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo={bid.bid_no}&bidPbancOrd={bid.bid_seq}" if bid.bid_no.startswith("R") else f"https://www.g2b.go.kr/pt/menu/selectSubFrame.do?framesrc=/ep/invitation/publish/bidInfoDtl.do?bidno={bid.bid_no}%26bidseq={bid.bid_seq}"
        })
    return data
