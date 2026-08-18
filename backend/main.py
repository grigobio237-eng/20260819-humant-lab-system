from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import datetime

from engine import get_recommended_est_rate, calculate_bid_price, check_qualification, fetch_a_value, get_lower_rate
from database import engine, get_db
import models

# 서버 시작 시 데이터베이스 테이블 자동 생성 (테스트용)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="휴먼트 랩 시스템 API",
    description="건설 입찰 공고 최적 투찰가 계산 및 적격심사 판별 백엔드 시스템입니다.",
    version="1.0.0"
)

# 프론트엔드 연동을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 개발용 (실서비스 시 프론트엔드 도메인으로 제한)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Schemas ---
class BidPayload(BaseModel):
    bid_full_no: str = Field(..., title="공고번호-차수", description="예: 20260818001-00")
    bid_no: str = Field(..., title="원본 공고번호")
    bid_seq: str = Field(..., title="공고 차수")
    bid_name: str = Field(..., title="공고명")
    client_name: str = Field(..., title="발주처")
    base_price: float = Field(..., title="기초금액", description="수집된 공고의 기초금액 (원)")
    a_value: float = Field(0.0, title="A값", description="A값 (국민연금 등 제외 대상 금액)")
    net_cost: float = Field(0.0, title="순공사원가", description="순공사원가 (98% 하한선 검증용)")
    lower_rate: float = Field(..., title="낙찰하한율", description="예: 0.87745 (87.745%)")
    range_min: float = Field(97.0, title="사정률 범위 하한", description="예: 97.0 (조달청)")
    range_max: float = Field(103.0, title="사정률 범위 상한", description="예: 103.0 (조달청)")
    deadline: datetime.datetime = Field(..., title="입찰 마감 일시")
    license_req: Optional[Dict[str, float]] = Field(None, title="요구 면허 조건")

class CompanyPayload(BaseModel):
    licenses: Dict[str, float] = Field(..., title="자사 보유 면허")
    
# --- Mock Data (과거 사정률 대체용) ---
MOCK_PAST_RATES = []

@app.get("/", summary="루트(Root) 상태 확인")
def read_root():
    return {"status": "ok", "message": "휴먼트 랩 시스템 API 정상 가동 중"}

import traceback

@app.post("/api/v1/test_calculate")
def test_process_new_bid(payload: BidPayload, company: CompanyPayload, db: Session = Depends(get_db)):
    try:
        existing_bid = db.query(models.Bid).filter(models.Bid.bid_full_no == payload.bid_full_no).first()
        fetched_a_value = fetch_a_value(payload.bid_no, payload.bid_seq)
        final_a_value = fetched_a_value if fetched_a_value > 0 else payload.a_value
        dynamic_lower_rate = get_lower_rate(payload.base_price, payload.client_name)
        is_qualified = check_qualification(payload.license_req or {}, company.licenses)
        recommended_est_rate = get_recommended_est_rate(MOCK_PAST_RATES, payload.range_min, payload.range_max, payload.client_name)
        calc_result = calculate_bid_price(payload.base_price, final_a_value, payload.net_cost, dynamic_lower_rate, recommended_est_rate)
        
        return {"status": "success", "recommended_est_rate": float(recommended_est_rate)}
    except Exception as e:
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

@app.post("/api/v1/calculate", summary="신규 공고 투찰가 계산 및 DB 적재")
def process_new_bid(payload: BidPayload, company: CompanyPayload, db: Session = Depends(get_db)):
    """
    n8n 자동화 봇에서 신규 공고 데이터를 넘겨줄 때 호출됩니다.
    계산 로직 수행 후 DB(bids, calculated_bids)에 저장합니다.
    """
    # 1. 기존에 같은 공고(bid_full_no)가 있는지 확인
    existing_bid = db.query(models.Bid).filter(models.Bid.bid_full_no == payload.bid_full_no).first()
    if existing_bid:
        return {"status": "skipped", "message": "이미 처리된 공고입니다."}

    # 2. A값 동적 수집 (n8n이 던져준 공고번호로 직접 조달청 API 호출)
    fetched_a_value = fetch_a_value(payload.bid_no, payload.bid_seq)
    final_a_value = fetched_a_value if fetched_a_value > 0 else payload.a_value

    # 3. 낙찰하한율 동적 계산 (기초금액 기준)
    dynamic_lower_rate = get_lower_rate(payload.base_price, payload.client_name)

    # 4. 적격심사 시뮬레이션
    is_qualified = check_qualification(payload.license_req or {}, company.licenses)
    
    # 5. 통계 엔진
    recommended_est_rate = get_recommended_est_rate(MOCK_PAST_RATES, payload.range_min, payload.range_max, payload.client_name)
    
    # 6. 투찰가 계산
    calc_result = calculate_bid_price(
        payload.base_price, final_a_value, payload.net_cost, dynamic_lower_rate, recommended_est_rate
    )
    
    # 7. 데이터베이스 저장 (원본 공고)
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
        deadline=payload.deadline
    )
    db.add(new_bid)
    
    # 8. 데이터베이스 저장 (계산 결과)
    new_calc = models.CalculatedBid(
        bid_full_no=payload.bid_full_no,
        is_qualified=is_qualified,
        recommended_est_rate=recommended_est_rate,
        calculated_bid_price=calc_result["calculated_bid_price"],
        is_net_cost_applied=calc_result["is_net_cost_applied"]
    )
    db.add(new_calc)
    db.commit()
    
    return {"status": "success", "bid_full_no": payload.bid_full_no}

@app.get("/api/v1/bids", summary="대시보드 표시용 전체 공고 목록 조회")
def get_bids(db: Session = Depends(get_db)):
    """
    프론트엔드(React) 대시보드 화면에 뿌려줄 입찰 공고 목록과 계산 결과를 가져옵니다.
    """
    results = db.query(models.Bid, models.CalculatedBid).outerjoin(
        models.CalculatedBid, models.Bid.bid_full_no == models.CalculatedBid.bid_full_no
    ).order_by(models.Bid.created_at.desc()).all()
    
    data = []
    for bid, calc in results:
        data.append({
            "bid_full_no": bid.bid_full_no,
            "bid_name": bid.bid_name,
            "client_name": bid.client_name,
            "base_price": float(bid.base_price),
            "range": f"{bid.range_min}% ~ {bid.range_max}%",
            "recommended_est_rate": float(calc.recommended_est_rate) if calc else 0.0,
            "calculated_bid_price": float(calc.calculated_bid_price) if calc else 0.0,
            "is_qualified": calc.is_qualified if calc else False,
            "deadline": bid.deadline.strftime("%Y-%m-%d %H:%M"),
            "status": calc.review_status if calc else "PENDING",
            "a_value": float(bid.a_value),
            "net_cost": float(bid.net_cost),
            "lower_rate": float(bid.lower_rate),
            "is_net_cost_applied": calc.is_net_cost_applied if calc else False,
            "link_url": f"https://www.g2b.go.kr:8081/ep/invitation/publish/bidInfoDtl.do?bidno={bid.bid_no}&bidseq={bid.bid_seq}"
        })
    return data
