from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, JSON, ARRAY, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(100), nullable=False)
    business_reg_no = Column(String(20), unique=True, nullable=False)
    region_code = Column(String(255))
    licenses = Column(JSON)
    management_score = Column(Numeric(5, 2))
    updated_at = Column(DateTime, default=datetime.utcnow)

class Bid(Base):
    __tablename__ = "bids"
    bid_full_no = Column(String(60), primary_key=True)
    bid_no = Column(String(50), nullable=False, index=True)
    bid_seq = Column(String(10), nullable=False)
    bid_name = Column(String(255), nullable=False)
    client_name = Column(String(100))
    region_code = Column(String(255))
    license_condition = Column(String, default="")
    region_condition = Column(String, default="")
    raw_data = Column(JSON, default={})
    base_price = Column(Numeric(15, 0), nullable=False)
    a_value = Column(Numeric(15, 0), default=0)
    net_cost = Column(Numeric(15, 0), default=0)
    lower_rate = Column(Numeric(5, 4), nullable=False)
    range_min = Column(Numeric(5, 2), default=97.00)
    range_max = Column(Numeric(5, 2), default=103.00)
    deadline = Column(DateTime, nullable=False)
    link_url = Column(String)
    status = Column(String(20), default="OPEN")
    created_at = Column(DateTime, default=datetime.utcnow)

class BidResult(Base):
    __tablename__ = "bid_results"
    bid_full_no = Column(String(60), ForeignKey("bids.bid_full_no"), primary_key=True)
    est_price = Column(Numeric(15, 0), nullable=False)
    est_rate = Column(Numeric(7, 5), nullable=False, index=True)
    winning_bid_price = Column(Numeric(15, 0))
    participant_count = Column(Integer)
    selected_pre_price_numbers = Column(ARRAY(Integer))
    created_at = Column(DateTime, default=datetime.utcnow)

class CalculatedBid(Base):
    __tablename__ = "calculated_bids"
    bid_full_no = Column(String(60), ForeignKey("bids.bid_full_no"), primary_key=True)
    is_qualified = Column(Boolean, nullable=False)
    recommended_est_rate = Column(Numeric(7, 5), nullable=False)
    calculated_bid_price = Column(Numeric(15, 0), nullable=False)
    is_net_cost_applied = Column(Boolean, default=False)
    review_status = Column(String(20), default="PENDING")
    updated_at = Column(DateTime, default=datetime.utcnow)
