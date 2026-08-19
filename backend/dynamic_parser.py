import re

def parse_bid_text(text: str, base_price: float = 0.0):
    extracted_a_value = 0.0
    extracted_lower_rate = 0.0
    a_value_breakdown = {}
    confidence_level = "LOW"
    
    # 1. 낙찰하한율 추출 (Layer 1)
    rate_patterns = [
        r"낙찰하한율\s*\(?(\d{2}\.\d+)\s*%\)?",
        r"(\d{2}\.\d+)\s*%\s*이상",
        r"100분의\s*(\d{2}\.\d+)",
        r"(\d{2}\.\d+)\s*퍼센트"
    ]
    
    for pat in rate_patterns:
        match = re.search(pat, text)
        if match:
            rate_val = float(match.group(1))
            if 80.0 <= rate_val <= 95.0:
                extracted_lower_rate = rate_val / 100.0
                confidence_level = "MEDIUM"
                break

    # 2. A값 추출 (Layer 2 & 1)
    keywords = {
        "국민연금": r"국민연금(?:보험료)?\s*[:\s]*금?\s*([\d,]+)\s*원?",
        "건강보험": r"건강보험(?:료)?\s*[:\s]*금?\s*([\d,]+)\s*원?",
        "노인장기요양": r"노인장기요양(?:보험료)?\s*[:\s]*금?\s*([\d,]+)\s*원?",
        "퇴직공제부금": r"퇴직공제(?:부금)?(?:비)?\s*[:\s]*금?\s*([\d,]+)\s*원?",
        "산업안전보건": r"산업안전보건(?:관리비)?\s*[:\s]*금?\s*([\d,]+)\s*원?",
        "안전관리비": r"(?:안전관리비|품질관리비)\s*[:\s]*금?\s*([\d,]+)\s*원?"
    }
    
    total_a = 0.0
    for key, pat in keywords.items():
        matches = re.findall(pat, text)
        if matches:
            val = float(matches[-1].replace(",", ""))
            if val > 0:
                a_value_breakdown[key] = val
                total_a += val
                
    if total_a == 0:
        a_sum_patterns = [
            r"\[A.*?\]\s*합(?:산|계)?금액\s*[:은]?\s*금?\s*([\d,]+)\s*원",
            r"A값\s*[:은]?\s*금?\s*([\d,]+)\s*원",
            r"비공제\s*항목\s*합산\s*[:은]?\s*금?\s*([\d,]+)\s*원",
            r"A\s*=\s*([\d,]+)"
        ]
        for pat in a_sum_patterns:
            match = re.search(pat, text)
            if match:
                val = float(match.group(1).replace(",", ""))
                if val > 0:
                    total_a = val
                    a_value_breakdown["합산금액(A)"] = val
                    break
                    
    extracted_a_value = total_a
    
    if base_price > 0:
        if extracted_a_value >= base_price or extracted_a_value < 0:
            extracted_a_value = 0.0
            a_value_breakdown = {}
            
    if 80.0 <= (extracted_lower_rate * 100) <= 95.0:
        if extracted_a_value > 0:
            confidence_level = "HIGH"
    else:
        extracted_lower_rate = 0.0
        
    return {
        "extracted_a_value": extracted_a_value,
        "extracted_lower_rate": extracted_lower_rate,
        "a_value_breakdown": a_value_breakdown,
        "confidence_level": confidence_level
    }