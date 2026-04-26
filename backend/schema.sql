-- YouthFit DB 스키마
-- Supabase (PostgreSQL) 기준
-- Supabase 대시보드 > SQL Editor에서 실행

-- =====================
-- users 테이블
-- 사용자 프로필 정보 (대화에서 자동 추출)
-- =====================
CREATE TABLE IF NOT EXISTS users (
    user_id               VARCHAR(255) PRIMARY KEY,
    age                   INTEGER,
    region                VARCHAR(100),
    job_status            VARCHAR(100),
    income_level          VARCHAR(100),
    housing_type          VARCHAR(100),
    household_size        INTEGER,
    unemployment_benefit  VARCHAR(50),   -- 예: 수급중 / 미수급 / 모름
    recent_work_history   VARCHAR(50),   -- 예: 있음 / 없음 / 모름
    updated_at            TIMESTAMP DEFAULT NOW()
);

-- =====================
-- conversations 테이블
-- 상담 세션 단위 메타데이터
-- =====================
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id  UUID PRIMARY KEY,
    user_id          VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    title            VARCHAR(255) DEFAULT '새 상담',
    started_at       TIMESTAMP DEFAULT NOW(),
    updated_at       TIMESTAMP DEFAULT NOW(),
    last_message_at  TIMESTAMP DEFAULT NOW()
);

-- =====================
-- messages 테이블
-- 사용자-챗봇 메시지 저장
-- =====================
CREATE TABLE IF NOT EXISTS messages (
    message_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id  UUID REFERENCES conversations(conversation_id) ON DELETE SET NULL,
    user_id          VARCHAR(255) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role             VARCHAR(20) NOT NULL,
    content          TEXT NOT NULL,
    message_type     VARCHAR(50) NOT NULL DEFAULT 'normal',
    metadata         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at       TIMESTAMP DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_users_updated_at ON users(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at ON conversations(last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_user_id_created_at ON messages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id_created_at ON messages(conversation_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_role ON messages(role);

-- 참고: 보존 정책 cleanup은 scripts/retention_cleanup.sql 참고
