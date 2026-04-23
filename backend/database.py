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
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Supabase 연결 성공!")
        return True
    except Exception as e:
        print(f"❌ Supabase 연결 실패: {e}")
        return False


# =====================
# 사용자 정보
# =====================

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
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
    with engine.connect() as conn:
        conn.execute(
            text("INSERT INTO users (user_id) VALUES (:user_id) ON CONFLICT DO NOTHING"),
            {"user_id": user_id}
        )
        conn.commit()
    return get_user(user_id) or {"user_id": user_id}


def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    create_user(user_id)

    valid_fields = ["age", "region", "job_status", "income_level", "housing_type", "interests"]
    filtered = {k: v for k, v in updates.items() if k in valid_fields and v is not None}

    if not filtered:
        return get_user(user_id)

    if "interests" in filtered and isinstance(filtered["interests"], list):
        filtered["interests"] = json.dumps(filtered["interests"], ensure_ascii=False)

    set_clause = ", ".join(f"{k} = :{k}" for k in filtered.keys())

    with engine.connect() as conn:
        conn.execute(
            text(f"UPDATE users SET {set_clause}, updated_at = NOW() WHERE user_id = :user_id"),
            {**filtered, "user_id": user_id}
        )
        conn.commit()

    return get_user(user_id)


def get_missing_fields(user_id: str) -> List[str]:
    user = get_user(user_id)
    if not user:
        return ["age", "region", "job_status"]
    return [f for f in ["age", "region", "job_status"] if not user.get(f)]


# =====================
# 대화 세션
# =====================

def create_conversation(conversation_id: str, user_id: str) -> None:
    create_user(user_id)
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO conversations (conversation_id, user_id, title)
                VALUES (:conversation_id, :user_id, '새 상담')
                ON CONFLICT DO NOTHING
            """),
            {"conversation_id": conversation_id, "user_id": user_id}
        )
        conn.commit()


def update_conversation_timestamp(conversation_id: str) -> None:
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE conversations
                SET last_message_at = NOW(), updated_at = NOW()
                WHERE conversation_id = :conversation_id
            """),
            {"conversation_id": conversation_id}
        )
        conn.commit()


# =====================
# 메시지
# =====================

def save_message(user_id: str, role: str, content: str,
                 conversation_id: Optional[str] = None,
                 extracted_info: Optional[Dict] = None,
                 message_type: str = "normal") -> None:
    create_user(user_id)

    metadata = {}
    if extracted_info:
        metadata["extracted_info"] = extracted_info

    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO messages
                    (conversation_id, user_id, role, content, message_type, metadata)
                VALUES
                    (:conversation_id, :user_id, :role, :content, :message_type, :metadata)
            """),
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "message_type": message_type,
                "metadata": json.dumps(metadata, ensure_ascii=False),
            }
        )
        conn.commit()

    if conversation_id:
        update_conversation_timestamp(conversation_id)


def get_chat_history(user_id: str, limit: int = 10,
                     conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """conversation_id가 있으면 해당 세션만, 없으면 user_id 기준 최근 메시지"""
    with engine.connect() as conn:
        if conversation_id:
            result = conn.execute(
                text("""
                    SELECT role, content, created_at
                    FROM messages
                    WHERE conversation_id = :conversation_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"conversation_id": conversation_id, "limit": limit}
            )
        else:
            result = conn.execute(
                text("""
                    SELECT role, content, created_at
                    FROM messages
                    WHERE user_id = :user_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {"user_id": user_id, "limit": limit}
            )
        rows = result.fetchall()

    return [dict(row._mapping) for row in reversed(rows)]


# 앱 시작 시 DB 연결 테스트
init_db()
