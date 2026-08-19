def calculate_est_price(base_price: float, a_value: float = 0, est_rate: float = 1.0) -> float:
    return float(base_price) * float(est_rate)

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
