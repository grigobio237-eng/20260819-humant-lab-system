import numpy as np
from scipy.stats import norm
from decimal import Decimal, ROUND_HALF_UP
import httpx
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
        response = httpx.get(url, params=params, timeout=10.0)
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

import random

def simulate_monte_carlo_est_rate(range_min: float, range_max: float, client_name: str, simulations: int = 10000) -> float:
    """
    조달청 복수예비가격 작성 기준(100% 초과 7~8개, 100% 이하 7~8개)을 모사한 몬테카를로 시뮬레이션
    """
    results = []
    mid_point = (range_min + range_max) / 2.0
    
    for _ in range(simulations):
        # 100% (mid_point)를 기준으로 위/아래 개수 결정 (7:8 또는 8:7)
        over_count = random.choice([7, 8])
        under_count = 15 - over_count
        
        # 15개의 복수예비가격 생성
        over_prices = [random.uniform(mid_point, range_max) for _ in range(over_count)]
        under_prices = [random.uniform(range_min, mid_point) for _ in range(under_count)]
        prices = over_prices + under_prices
        
        # 15개 중 무작위로 4개 추첨
        selected = random.sample(prices, 4)
        
        # 4개의 평균 산출 (사정률)
        avg_rate = sum(selected) / 4.0
        results.append(avg_rate)
    
    # 최빈구간(1-sigma) 탐색을 위해 평균(기댓값) 계산
    mu, std = norm.fit(results)
    
    # 동가 입찰(추첨 탈락) 방지를 위한 정밀 분산 오프셋 (Jitter)
    # -0.0050% ~ +0.0050% 사이의 미세한 랜덤 값을 더해 100.0000% 정중앙을 회피
    jitter = random.uniform(-0.0050, 0.0050)
    
    optimal_rate = mu + jitter
    return optimal_rate

def get_recommended_est_rate(past_est_rates: list[float], range_min: float, range_max: float, client_name: str) -> Decimal:
    """
    과거 사정률 데이터를 바탕으로 정규분포(가우시안)를 분석하여 최상위 빈도수(평균값 주변) 구간의 사정률 추천.
    발주처(client_name) 및 사정률 구간별로 필터링된 과거 데이터를 입력받음.
    """
    if not past_est_rates or len(past_est_rates) < 10:
        # 데이터가 부족한 경우 몬테카를로 시뮬레이터 가동
        simulated_rate = simulate_monte_carlo_est_rate(range_min, range_max, client_name)
        # 퍼센티지를 비율로 변환 (예: 100.2345 -> 1.002345)
        return Decimal(str(simulated_rate / 100.0)).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
    
    # 과거 낙찰 데이터가 충분할 경우, 정규분포 피팅
    mu, std = norm.fit(past_est_rates)
    
    # 과거 데이터 기반일 때도 동가 입찰 방지를 위해 미세 오프셋 적용
    jitter = random.uniform(-0.0050, 0.0050)
    optimal_rate = mu + jitter
    
    # 퍼센티지를 비율로 변환하여 반환
    return Decimal(str(optimal_rate / 100.0)).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)

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

def check_qualification(
    license_condition: str,
    region_condition: str,
    company_licenses: dict,
    company_region: str,
    bid_name: str = "",
    base_price: float = 0.0
) -> bool:
    if not license_condition and not region_condition and not bid_name:
        return False

    is_national = "전국" in region_condition or "전 국" in region_condition
    if not is_national:
        if not company_region:
            return False
            
        comp_region_parts = company_region.split()
        comp_main_region = comp_region_parts[0][:2] if comp_region_parts else ""
        
        combined_region_text = (region_condition + " " + bid_name)
        if comp_main_region not in combined_region_text and company_region not in combined_region_text:
            return False

    if not company_licenses:
        return False
        
    has_matching_license = False
    clean_license_cond = (license_condition + " " + bid_name).replace(" ", "")
    
    for comp_license, limit_amount in company_licenses.items():
        clean_comp_license = comp_license.replace(" ", "")
        if clean_comp_license in clean_license_cond:
            if limit_amount and float(limit_amount) > 0:
                if float(base_price) > float(limit_amount):
                    continue
            has_matching_license = True
            break
            
    if not has_matching_license:
        return False
        
    blacklist_keywords = [
        "전기", "정보통신", "통신", "소방", "승강기", "토목", "조경", 
        "기계설비", "배수", "산사태", "아스콘", "도로", "폐기물", "용역", "물품", "해체"
    ]
    
    for bl_kw in blacklist_keywords:
        if bl_kw in clean_license_cond:
            has_bl_license = any(bl_kw in c_lic.replace(" ", "") for c_lic in company_licenses.keys())
            if not has_bl_license:
                return False

    return True
