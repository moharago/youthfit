-- YouthFit DB 스키마
-- Supabase (PostgreSQL) 기준
-- Supabase 대시보드 > SQL Editor에서 실행

-- =====================
-- users 테이블
-- 사용자 프로필 정보 (대화에서 자동 추출)
-- =====================
CREATE TABLE IF NOT EXISTS users (
    user_id     VARCHAR(255) PRIMARY KEY,
    age         INTEGER,
    region      VARCHAR(100),          -- 예: 서울, 부산
    job_status  VARCHAR(100),          -- 예: 취업준비중, 재직중, 무직
    income_level VARCHAR(100),         -- 예: 중위소득 60% 이하
    housing_type VARCHAR(100),         -- 예: 전세, 월세, 자가
    interests   TEXT,                  -- JSON 배열 문자열 ["취업", "주거"]
    updated_at  TIMESTAMP DEFAULT NOW()
);

-- =====================
-- chat_history 테이블
-- 사용자-챗봇 대화 이력
-- =====================
CREATE TABLE IF NOT EXISTS chat_history (
    id              SERIAL PRIMARY KEY,
    user_id         VARCHAR(255) NOT NULL REFERENCES users(user_id),
    role            VARCHAR(20) NOT NULL,   -- 'user' 또는 'assistant'
    content         TEXT NOT NULL,
    extracted_info  TEXT,                   -- JSON 문자열 (추출된 사용자 정보)
    timestamp       TIMESTAMP DEFAULT NOW()
);

-- 인덱스 (대화 이력 조회 성능)
CREATE INDEX IF NOT EXISTS idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_history_timestamp ON chat_history(timestamp DESC);

-- ※ 30일 보존 정책 cleanup은 scripts/retention_cleanup.sql 참고
