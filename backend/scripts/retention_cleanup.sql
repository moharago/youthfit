-- 30일 지난 대화 이력 삭제
-- Supabase SQL Editor에서 수동 실행하거나 pg_cron으로 자동화
DELETE FROM chat_history WHERE timestamp < NOW() - INTERVAL '30 days';
