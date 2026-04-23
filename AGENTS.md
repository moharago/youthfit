# YouthFit — Codex 작업 가이드

## 프로젝트 한 줄 요약
청년 정책 맞춤형 AI 상담 챗봇. RAG 기반으로 정책 문서만 활용해 환각 없이 답변.

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React + Vite (pnpm) → Vercel 배포 |
| Backend | FastAPI → Railway 배포 |
| LLM | OpenAI GPT-4o-mini |
| Embedding | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB (backend/data/chroma_db/) |
| DB | Supabase (PostgreSQL) |

---

## 폴더 구조 핵심

```
backend/
├── main.py          # FastAPI 엔드포인트, LLM/임베딩 초기화
├── router.py        # 질문 분류 (ASK_CLARIFY / RAG_REWRITE / RAG_DIRECT)
├── ingest.py        # 정책 문서 → ChromaDB 벡터화
├── database.py      # DB 연결 & 쿼리 (Supabase PostgreSQL)
├── user_service.py  # 사용자 정보 추출 & 저장
├── data/files/      # 원본 정책 문서 (CSV, PDF, Excel, JSON)
└── .env             # API 키 (절대 커밋 금지)

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

- git 작업은 사용자가 직접 함 — Codex는 git 명령어 실행 금지
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

## 현재 진행 중인 작업 (배포 고도화)

1. ✅ LLM: Ollama → OpenAI GPT-4o-mini 교체 완료
2. ✅ 임베딩: HuggingFace → OpenAI text-embedding-3-small 교체 완료
3. ✅ DB: MySQL → Supabase(PostgreSQL) 교체 완료
4. ✅ Frontend: Vite + React 세팅 완료 (VITE_API_URL 환경변수 처리)
5. ⬜ Backend 배포: Railway
6. ⬜ Frontend 배포: Vercel

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

## 주요 LLM 관련 코드 위치

- LLM 초기화: `backend/main.py` 58번째 줄 근처 (`ChatOpenAI`)
- 임베딩 초기화: `backend/main.py` 44번째 줄 근처 (`OpenAIEmbeddings`)
- 프롬프트: `backend/main.py` 63~109번째 줄
- 라우터 프롬프트: `backend/router.py` 54~108번째 줄
