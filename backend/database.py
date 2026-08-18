from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# 서버 컴퓨터의 PostgreSQL에 접속하기 위한 설정입니다.
# 로컬 테스트 시에는 SQLite를 사용하도록 분기처리할 수도 있습니다.
# 예시: "postgresql+pg8000://humant_admin:humant_password@<서버IP>:5432/humant_db"

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./humant_local_test.db")

# SQLite 사용 시 쓰레드 체크 비활성화 (PostgreSQL 연동 시엔 connect_args 삭제)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
