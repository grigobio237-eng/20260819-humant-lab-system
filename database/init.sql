-- 휴먼트 랩 시스템 데이터베이스 초기화 스크립트 (버전 1.1)
-- Docker 컨테이너 최초 실행 시 자동 적용됩니다.

-- 1. 자사 프로필 및 적격심사 기준 테이블
CREATE TABLE IF NOT EXISTS company_profiles (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    business_reg_no VARCHAR(20) UNIQUE NOT NULL, -- 사업자등록번호
    region_code VARCHAR(255), -- 주영업소 지역코드
    licenses JSONB, -- 보유 면허 및 시공능력평가액 (예: {"건축": 1000000000, "토목": 500000000})
    management_score NUMERIC(5,2), -- 경영상태 평가점수 (만점 기준)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 입찰 공고 원본 데이터 테이블
CREATE TABLE IF NOT EXISTS bids (
    bid_full_no VARCHAR(60) PRIMARY KEY, -- 공고번호-차수 복합키 (예: 20260818001-00)
    bid_no VARCHAR(50) NOT NULL, -- 원본 공고번호 (bidNtceNo)
    bid_seq VARCHAR(10) NOT NULL, -- 차수 (bidNtceOrd)
    bid_name VARCHAR(255) NOT NULL, -- 공고명
    client_name VARCHAR(100), -- 발주처/수요기관
    region_code VARCHAR(255), -- 공고 지역코드
    license_condition TEXT, -- 요구 면허 조건
    region_condition TEXT, -- 지역 제한 조건
    raw_data JSONB, -- 원본 데이터
    base_price NUMERIC(15,0) NOT NULL, -- 기초금액 (P_base)
    a_value NUMERIC(15,0) DEFAULT 0, -- A값
    net_cost NUMERIC(15,0) DEFAULT 0, -- 순공사원가 (C_net)
    lower_rate NUMERIC(5,4) NOT NULL, -- 낙찰하한율 (R_lower)
    range_min NUMERIC(5,2) DEFAULT 97.00, -- 사정률 범위 하한선 (%) (예: 조달청 97, 한전 98)
    range_max NUMERIC(5,2) DEFAULT 103.00, -- 사정률 범위 상한선 (%) (예: 조달청 103, 한전 102)
    deadline TIMESTAMP NOT NULL, -- 입찰 마감 일시
    link_url TEXT, -- 나라장터 수동 투찰 바로가기 URL
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, CLOSED, CANCELED
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 원본 공고번호 단위 조회를 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_bids_bid_no ON bids(bid_no);

-- 3. 과거 개찰 결과 및 통계 데이터 테이블
CREATE TABLE IF NOT EXISTS bid_results (
    bid_full_no VARCHAR(60) PRIMARY KEY REFERENCES bids(bid_full_no),
    est_price NUMERIC(15,0) NOT NULL, -- 확정 예정가격
    est_rate NUMERIC(7,5) NOT NULL, -- 결정된 사정률 (예정가격/기초금액)
    winning_bid_price NUMERIC(15,0), -- 1순위 투찰가
    participant_count INT, -- 참여 업체 수
    selected_pre_price_numbers INT[], -- 추첨된 예비가격 번호 4개 (예: '{1, 5, 8, 14}')
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 사정률 분석 속도 향상을 위한 인덱스
CREATE INDEX IF NOT EXISTS idx_bid_results_est_rate ON bid_results(est_rate);

-- 4. 시뮬레이션 및 투찰가 계산 결과 테이블
CREATE TABLE IF NOT EXISTS calculated_bids (
    bid_full_no VARCHAR(60) PRIMARY KEY REFERENCES bids(bid_full_no),
    is_qualified BOOLEAN NOT NULL, -- 적격심사 만점(O/X) 시뮬레이션 결과
    recommended_est_rate NUMERIC(7,5) NOT NULL, -- 통계 엔진이 추천한 사정률 (R_est)
    calculated_bid_price NUMERIC(15,0) NOT NULL, -- 수리 모델을 거친 최종 투찰가 (P_bid)
    is_net_cost_applied BOOLEAN DEFAULT FALSE, -- 순공사원가 하한선(98%) 적용 여부
    review_status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, REVIEWED, SUBMITTED (사용자 확인 상태)
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
