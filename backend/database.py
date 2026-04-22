# database.py (Supabase PostgreSQL 버전)

import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다. backend/.env를 확인하세요.")

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    echo=False
)


def init_db():
    """DB 연결 테스트"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Supabase 연결 성공!")
        return True
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False


# =====================
# 사용자 정보 관련
# =====================

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 정보 조회"""
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT * FROM users WHERE user_id = :user_id"),
            {"user_id": user_id}
        )
        row = result.fetchone()

        if row:
            user = dict(row._mapping)
            if user.get("interests") and isinstance(user["interests"], str):
                user["interests"] = json.loads(user["interests"])
            return user
    return None


def create_user(user_id: str) -> Dict[str, Any]:
    """새 사용자 생성"""
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO users (user_id) VALUES (:user_id) ON CONFLICT DO NOTHING"),
            {"user_id": user_id}
        )
        conn.commit()

    return get_user(user_id) or {"user_id": user_id}


def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """사용자 정보 업데이트"""
    create_user(user_id)

    valid_fields = ["age", "region", "job_status", "income_level", "housing_type", "interests"]
    filtered = {k: v for k, v in updates.items() if k in valid_fields and v is not None}

    if not filtered:
        return get_user(user_id)

    if "interests" in filtered and isinstance(filtered["interests"], list):
        filtered["interests"] = json.dumps(filtered["interests"], ensure_ascii=False)

    set_parts = [f"{k} = :{k}" for k in filtered.keys()]
    set_clause = ", ".join(set_parts)

    with engine.connect() as conn:
        conn.execute(
            text(f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE user_id = :user_id"),
            {**filtered, "user_id": user_id}
        )
        conn.commit()

    return get_user(user_id)


def get_missing_fields(user_id: str) -> List[str]:
    """부족한 필수 정보 확인"""
    user = get_user(user_id)
    if not user:
        return ["age", "region", "job_status"]

    required = ["age", "region", "job_status"]
    return [field for field in required if not user.get(field)]


# =====================
# 대화 기록 관련
# =====================

def save_message(user_id: str, role: str, content: str, extracted_info: Dict = None):
    """대화 저장"""
    create_user(user_id)

    extracted_json = json.dumps(extracted_info, ensure_ascii=False) if extracted_info else None

    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO chat_history (user_id, role, content, extracted_info)
                VALUES (:user_id, :role, :content, :extracted_info)
            """),
            {
                "user_id": user_id,
                "role": role,
                "content": content,
                "extracted_info": extracted_json
            }
        )
        conn.commit()


def get_chat_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """최근 대화 기록 조회"""
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT role, content, timestamp
                FROM chat_history
                WHERE user_id = :user_id
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": limit}
        )
        rows = result.fetchall()

    return [dict(row._mapping) for row in reversed(rows)]


def get_chat_context(user_id: str, limit: int = 5) -> str:
    """LLM에 넣을 대화 컨텍스트 생성"""
    history = get_chat_history(user_id, limit)

    if not history:
        return ""

    context = "이전 대화:\n"
    for msg in history:
        role = "사용자" if msg["role"] == "user" else "챗봇"
        context += f"{role}: {msg['content']}\n"

    return context


# 앱 시작 시 DB 연결 테스트
init_db()
