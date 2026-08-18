import numpy as np
from scipy.stats import norm
from decimal import Decimal, ROUND_HALF_UP

def get_recommended_est_rate(past_est_rates: list[float], range_min: float, range_max: float) -> Decimal:
    """
    과거 사정률 데이터를 바탕으로 정규분포(가우시안)를 분석하여 최상위 빈도수(평균값 주변) 구간의 사정률 추천.
    만약 과거 데이터가 부족하면 허용 범위(range_min ~ range_max)의 중간값을 반환.
    """
    if not past_est_rates or len(past_est_rates) < 10:
        # 데이터가 부족한 경우 중간값 (예: 97~103 이면 100)
        mid_val = (range_min + range_max) / 2
        # 퍼센티지를 비율로 변환 (예: 100 -> 1.0)
        return Decimal(str(mid_val / 100.0)).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
    
    # 정규분포 피팅 (평균과 표준편차)
    mu, std = norm.fit(past_est_rates)
    
    # 평균값을 최적 사정률로 선택 (향후 최빈값이나 특정 확률 분포 구간으로 고도화 가능)
    # 비율로 반환
    recommended_rate = Decimal(str(mu)).quantize(Decimal('0.00001'), rounding=ROUND_HALF_UP)
    return recommended_rate

def calculate_bid_price(base_price: float, a_value: float, net_cost: float, lower_rate: float, est_rate: Decimal) -> dict:
    """
    투찰가 산식 적용 엔진
    base_price: 기초금액 (P_base)
    a_value: A값
    net_cost: 순공사원가 (C_net)
    lower_rate: 낙찰하한율 (R_lower)
    est_rate: 사정률 (R_est)
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
    
    # 원단위 절상 (또는 절사 기준에 맞춰 적용 - 보통 0원 단위 절상)
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
    """
    적격심사 시뮬레이터 (간단화된 예시)
    공고가 요구하는 면허가 자사 프로필에 모두 있는지 검증
    """
    if not bid_license_req:
        return True
        
    for req_license, req_amount in bid_license_req.items():
        if req_license not in company_licenses:
            return False
        # 요구 시공능력평가액 조건이 있다면 검증
        if float(company_licenses[req_license]) < float(req_amount):
            return False
            
    return True
