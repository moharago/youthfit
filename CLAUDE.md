# YouthFit — Claude 작업 가이드

## 프로젝트 한 줄 요약
청년 정책 맞춤형 AI 상담 챗봇. RAG 기반으로 정책 문서만 활용해 환각 없이 답변.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React + Vite (pnpm) → Vercel 배포 |
| Backend | FastAPI → AWS 배포 |
| LLM | OpenAI GPT-4o-mini |
| Embedding | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (backend/data/chroma_db/) |
| DB | Supabase (PostgreSQL) |

---

## 폴더 구조 핵심

```
backend/
├── main.py              # FastAPI 엔드포인트, LLM/임베딩 초기화
├── router.py            # 질문 분류 (ASK_CLARIFY / RAG_REWRITE / RAG_DIRECT)
├── ingest.py            # 정책 문서 → ChromaDB 벡터화
├── database.py          # DB 연결 & 쿼리 (Supabase PostgreSQL)
├── user_service.py      # 사용자 정보 추출 & 저장
├── clarify_service.py   # 추가 정보 요청 옵션 정의
├── profile_schema.py    # 사용자 프로필 필드 상수 (단일 진실의 원천)
├── schema.sql           # Supabase 테이블 정의
├── scripts/
│   └── retention_cleanup.sql  # 30일 이상 메시지 정리 쿼리
├── report/              # 정책 리포트 생성 모듈
├── data/files/          # 원본 정책 문서 (CSV, PDF, Excel, JSON)
└── .env                 # API 키 (절대 커밋 금지)

frontend/
├── index.html       # Vite 진입 HTML (루트에 위치)
├── vite.config.js   # Vite 설정
├── package.json     # 의존성 (React 18, Vite 5)
├── .env.example     # 환경변수 템플릿
└── src/
    ├── main.jsx     # 앱 진입점
    ├── App.jsx      # 챗봇 UI (VITE_API_URL 환경변수로 API 호출)
    └── App.css      # 스타일
```

---

## 브랜치 규칙

- git 작업은 사용자가 직접 함 — Claude는 git 명령어 실행 금지
- 브랜치는 작업 단위별로 생성
  - `feat/` — 새 기능
  - `fix/` — 버그 수정
  - `chore/` — 설정, 패키지 등
  - `docs/` — 문서
- PR 생성 후 CodeRabbit 자동 리뷰 → 머지

---

## 절대 하지 말 것

- **git 명령어 절대 실행 금지** — commit, push, branch, merge 등 모든 git 작업은 사용자가 직접 함

---

## 작업 시 필수 규칙

- `.env` 절대 커밋하지 말 것 (OPENAI_API_KEY 포함)
- `frontend/node_modules/`, `backend/data/chroma_db/`, `venv/` 커밋 금지 (.gitignore 적용됨)
- `ingest.py` 수정하거나 정책 문서 추가하면 반드시 재실행해야 함
- API URL은 하드코딩 금지 — 환경변수로만 처리

---

## DB 스키마 (Supabase)

| 테이블 | 주요 컬럼 |
|--------|-----------|
| `users` | user_id, age, region, job_status, income_level, housing_type, household_size, unemployment_benefit, recent_work_history |
| `conversations` | conversation_id (uuid), user_id, title, started_at, updated_at, last_message_at |
| `messages` | message_id (uuid), conversation_id, user_id, role, content, message_type, metadata (jsonb), created_at |

- `conversation_id`: 브라우저 로드마다 새로 생성 → localStorage 보관 → API 요청에 포함
- LLM context 조회는 반드시 `conversation_id` 기준 (`get_chat_history`에 전달)
- `messages.metadata`에 `extracted_info` jsonb로 저장

---

## 현재 진행 중인 작업 (배포 고도화)

1. ✅ LLM: Ollama → OpenAI GPT-4o-mini 교체 완료
2. ✅ 임베딩: HuggingFace → OpenAI text-embedding-3-small 교체 완료
3. ✅ DB: MySQL → Supabase(PostgreSQL) 교체 완료
4. ✅ Frontend: Vite + React UI 개편 완료 (카테고리·빠른질문·채팅 통합)
5. ✅ DB 스키마: chat_history → messages 전환, conversations 세션 관리 추가
6. ✅ 실제 정책 데이터 수집 및 ingest
7. ⬜ Backend 배포: AWS
8. ⬜ Frontend 배포: Vercel

---

## 슬래시 커맨드

| 커맨드 | 역할 |
|--------|------|
| `/ingest` | 정책 문서 벡터화 재실행 |
| `/run-backend` | FastAPI 서버 실행 |
| `/run-frontend` | React 개발 서버 실행 |
| `/deploy-check` | 배포 전 체크리스트 |
| `/add-policy` | 새 정책 파일 추가 & DB 재구축 |

---

## 주요 코드 위치

- LLM 초기화: `backend/main.py` (`ChatOpenAI`, `OpenAIEmbeddings`)
- 프롬프트: `backend/main.py` (`prompt = ChatPromptTemplate...`)
- 라우터 프롬프트: `backend/router.py`
- clarify 옵션 정의: `backend/clarify_service.py` (`FIELD_OPTIONS`)
- 프로필 필드 상수: `backend/profile_schema.py` (`USER_PROFILE_FIELDS`, `ROUTER_MISSING_FIELDS`)
- 세션 생성/조회: `backend/database.py` (`create_conversation`, `get_chat_history`)
