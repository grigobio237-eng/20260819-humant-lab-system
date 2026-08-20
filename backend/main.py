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
    scraped_data = asyncio.run(scrape_g2b_details(payload.bid_no, payload.bid_seq, payload.bid_full_no, payload.base_price))
    
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
            
        # A값 및 하한율 파싱 데이터 적용
        payload.raw_data["scraped_a_value"] = scraped_data.get("extracted_a_value", 0.0)
        payload.raw_data["scraped_lower_rate"] = scraped_data.get("extracted_lower_rate", 0.0)
        payload.raw_data["a_value_breakdown"] = scraped_data.get("a_value_breakdown", {})
        payload.raw_data["confidence_level"] = scraped_data.get("confidence_level", "LOW")

    fetched_a_value = fetch_a_value(payload.bid_no, payload.bid_seq)
    
    # 파싱된 A값 최우선 적용, 그 다음 API 조회값, 그 다음 payload 값
    if payload.raw_data.get("scraped_a_value", 0.0) > 0:
        final_a_value = payload.raw_data["scraped_a_value"]
    else:
        final_a_value = fetched_a_value if fetched_a_value > 0 else payload.a_value
        
    # 파싱된 하한율 최우선 적용
    if payload.raw_data.get("scraped_lower_rate", 0.0) > 0:
        dynamic_lower_rate = payload.raw_data["scraped_lower_rate"]
    else:
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

from fastapi.responses import FileResponse
import os
import glob
from kapt_scraper import scrape_kapt_bids
from engine import calculate_bid_price, get_lower_rate, get_recommended_est_rate

@app.get("/api/v1/kapt/sync")
def sync_kapt_bids(limit: int = 10, db: Session = Depends(get_db)):
    import asyncio
    kapt_bids = asyncio.run(scrape_kapt_bids(limit))
    saved_count = 0
    
    for b in kapt_bids:
        existing = db.query(models.Bid).filter(models.Bid.bid_full_no == b["bid_full_no"]).first()
        if not existing:
            # 기본값 세팅 및 투찰가 계산
            dynamic_lower_rate = b.get("extracted_lower_rate") if b.get("extracted_lower_rate") > 0 else get_lower_rate(b["base_price"], b["client_name"])
            recommended_est_rate = get_recommended_est_rate([], 97.0, 103.0, b["client_name"])
            
            calc_result = calculate_bid_price(
                b["base_price"], 
                b["extracted_a_value"], 
                0.0, 
                dynamic_lower_rate, 
                recommended_est_rate
            )
            
            new_bid = models.Bid(
                bid_full_no=b["bid_full_no"],
                bid_no=b["bid_no"],
                bid_seq=b["bid_seq"],
                bid_name=b["bid_name"],
                client_name=b["client_name"],
                base_price=b["base_price"],
                a_value=b["extracted_a_value"],
                net_cost=0.0,
                lower_rate=dynamic_lower_rate,
                range_min=97.0,
                range_max=103.0,
                deadline=b["deadline"],
                license_condition=b["license_condition"],
                region_condition=b["region_condition"],
                raw_data={
                    "scraped_a_value": b["extracted_a_value"],
                    "scraped_lower_rate": b["extracted_lower_rate"],
                    "a_value_breakdown": b["a_value_breakdown"],
                    "confidence_level": b["confidence_level"],
                    "source": "K-apt"
                }
            )
            db.add(new_bid)
            db.commit()
            db.refresh(new_bid)
            
            new_calc = models.CalculatedBid(
                bid_full_no=new_bid.bid_full_no,
                is_qualified=False,
                recommended_est_rate=recommended_est_rate,
                calculated_bid_price=calc_result["calculated_bid_price"],
                is_net_cost_applied=calc_result["is_net_cost_applied"]
            )
            db.add(new_calc)
            db.commit()
            saved_count += 1
            
    return {"status": "success", "scraped": len(kapt_bids), "saved": saved_count}

@app.get("/api/v1/bids/{bid_full_no}/download")
def download_attachment(bid_full_no: str):
    dir_path = f"storage/attachments/{bid_full_no}"
    if os.path.exists(dir_path):
        files = glob.glob(f"{dir_path}/*")
        if files:
            # 첫 번째 첨부파일 다운로드
            return FileResponse(path=files[0], filename=os.path.basename(files[0]))
    raise HTTPException(status_code=404, detail="File not found")

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
            
        if bid.bid_full_no.startswith("KAPT-"):
            link_url = "https://www.k-apt.go.kr/bid/bidList.do"
        else:
            link_url = f"https://www.g2b.go.kr/link/PNPE027_01/single/?bidPbancNo={bid.bid_no}&bidPbancOrd={bid.bid_seq}" if bid.bid_no.startswith("R") else f"https://www.g2b.go.kr/pt/menu/selectSubFrame.do?framesrc=/ep/invitation/publish/bidInfoDtl.do?bidno={bid.bid_no}%26bidseq={bid.bid_seq}"
            
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
            "link_url": link_url
        })
    return data


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
