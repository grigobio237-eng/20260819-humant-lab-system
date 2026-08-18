import numpy as np
from scipy.stats import norm
from decimal import Decimal, ROUND_HALF_UP
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_a_value(bid_no: str, bid_seq: str) -> float:
    """
    조달청 OpenAPI (입찰가격산식A정보조회)를 호출하여 A값을 가져옵니다. (동기식)
    """
    service_key = "06729b226c522143633d5b32cb343affcb4b20bc8b9c96627f9c109a65e7ab96"
    url = "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListBidPrceCalclAInfo"
    params = {
        "ServiceKey": service_key,
        "numOfRows": "1",
        "pageNo": "1",
        "inqryDiv": "2",
        "bidNtceNo": bid_no,
        "type": "json"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10.0)
        if response.status_code == 200:
            data = response.json()
            items = data.get("response", {}).get("body", {}).get("items", [])
            if items:
                item = items[0]
                a_value = float(item.get("totAValAmount", item.get("aValue", 0.0)))
                
                if a_value == 0.0:
                    npn = float(item.get('ntnlPenInsPrmAmount', 0.0))
                    hth = float(item.get('hlthInsPrmAmount', 0.0))
                    rtm = float(item.get('rtrmntDedcAmnt', 0.0))
                    isaf = float(item.get('indstSftyHlthMngmntCst', 0.0))
                    a_value = npn + hth + rtm + isaf
                
                logger.info(f"[{bid_no}] A값 수집 완료: {a_value}")
                return a_value
    except Exception as e:
        logger.error(f"[{bid_no}] A값 수집 실패: {str(e)}")
    
    return 0.0

def get_lower_rate(base_price: float, client_name: str) -> float:
    """
    기초금액과 발주처에 따른 낙찰하한율(R_lower) 결정 로직
    """
    # 임시 하드코딩된 규칙 (조달청 시설공사 적격심사 세부기준 기준)
    # 실제로는 100억, 50억, 10억 미만 등 더 세밀한 기준과 조달청/지자체/국방부 구분이 필요
    
    if base_price < 1_000_000_000:
        return 0.87745
    elif base_price < 5_000_000_000:
        return 0.86745
    else:
        # 50억 이상 ~ 100억 미만
        return 0.85495

def get_recommended_est_rate(past_est_rates: list[float], range_min: float, range_max: float) -> Decimal:
    """
    과거 사정률 데이터를 바탕으로 정규분포(가우시안)를 분석하여 최상위 빈도수(평균값 주변) 구간의 사정률 추천.
    """
    if not past_est_rates or len(past_est_rates) < 10:
        mid_val = (range_min + range_max) / 2
        return Decimal(str(mid_val / 100.0)).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
    
    mu, std = norm.fit(past_est_rates)
    recommended_rate = Decimal(str(mu)).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
    return recommended_rate

def calculate_bid_price(base_price: float, a_value: float, net_cost: float, lower_rate: float, est_rate: Decimal) -> dict:
    """
    투찰가 산식 적용 엔진
    """
    P_base = Decimal(str(base_price))
    A = Decimal(str(a_value))
    C_net = Decimal(str(net_cost))
    R_lower = Decimal(str(lower_rate))
    R_est = est_rate
    
    # 예정가격 = 기초금액 * 사정률
    est_price = P_base * R_est
    
    # 1. A값 반영 산식: [(예정가격 - A) * 낙찰하한율] + A
    raw_bid_price = ((est_price - A) * R_lower) + A
    
    # 원단위 절상
    raw_bid_price = raw_bid_price.quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    
    # 2. 순공사원가 하한선(98%) 검증
    net_limit = (C_net * Decimal('0.98')).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
    
    is_net_cost_applied = False
    final_bid_price = raw_bid_price
    
    if final_bid_price < net_limit:
        final_bid_price = net_limit
        is_net_cost_applied = True
        
    return {
        "calculated_bid_price": final_bid_price,
        "is_net_cost_applied": is_net_cost_applied,
        "raw_bid_price": raw_bid_price,
        "net_limit": net_limit
    }

def check_qualification(bid_license_req: dict, company_licenses: dict) -> bool:
    if not bid_license_req:
        return True
        
    for req_license, req_amount in bid_license_req.items():
        if req_license not in company_licenses:
            return False
        if float(company_licenses[req_license]) < float(req_amount):
            return False
            
    return True
