# database.py

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

DB_PATH = "youthfit.db"

def init_db():
    """DB 초기화 - 테이블 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 사용자 정보 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            age INTEGER,
            region TEXT,
            job_status TEXT,
            income_level TEXT,
            housing_type TEXT,
            interests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 대화 기록 테이블
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            content TEXT,
            extracted_info TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ DB 초기화 완료")


# =====================
# 사용자 정보 관련
# =====================

def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """사용자 정보 조회"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        user = dict(row)
        # interests는 JSON 파싱
        if user.get("interests"):
            user["interests"] = json.loads(user["interests"])
        return user
    return None


def create_user(user_id: str) -> Dict[str, Any]:
    """새 사용자 생성"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()
    conn.close()
    
    return get_user(user_id) or {"user_id": user_id}


def update_user(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """사용자 정보 업데이트"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 사용자가 없으면 생성
    create_user(user_id)
    
    # 업데이트할 필드 필터링
    valid_fields = ["age", "region", "job_status", "income_level", "housing_type", "interests"]
    filtered_updates = {k: v for k, v in updates.items() if k in valid_fields and v is not None}
    
    if not filtered_updates:
        conn.close()
        return get_user(user_id)
    
    # interests는 JSON으로 저장
    if "interests" in filtered_updates:
        filtered_updates["interests"] = json.dumps(filtered_updates["interests"], ensure_ascii=False)
    
    # UPDATE 쿼리 생성
    set_clause = ", ".join([f"{k} = ?" for k in filtered_updates.keys()])
    set_clause += ", updated_at = ?"
    values = list(filtered_updates.values()) + [datetime.now(), user_id]
    
    cursor.execute(
        f"UPDATE users SET {set_clause} WHERE user_id = ?",
        values
    )
    conn.commit()
    conn.close()
    
    return get_user(user_id)


def get_missing_fields(user_id: str) -> List[str]:
    """부족한 필수 정보 확인"""
    user = get_user(user_id)
    if not user:
        return ["age", "region", "job_status"]
    
    required = ["age", "region", "job_status"]
    missing = [field for field in required if not user.get(field)]
    return missing


# =====================
# 대화 기록 관련
# =====================

def save_message(user_id: str, role: str, content: str, extracted_info: Dict = None):
    """대화 저장"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    extracted_json = json.dumps(extracted_info, ensure_ascii=False) if extracted_info else None
    
    cursor.execute(
        "INSERT INTO chat_history (user_id, role, content, extracted_info) VALUES (?, ?, ?, ?)",
        (user_id, role, content, extracted_json)
    )
    conn.commit()
    conn.close()


def get_chat_history(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """최근 대화 기록 조회"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content, timestamp 
        FROM chat_history 
        WHERE user_id = ? 
        ORDER BY timestamp DESC 
        LIMIT ?
    """, (user_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    # 시간순 정렬 (오래된 것 먼저)
    return [dict(row) for row in reversed(rows)]


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


# 앱 시작 시 DB 초기화
init_db()