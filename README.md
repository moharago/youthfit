[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/fNIvjsmp)

# 청년 정책 맞춤형 AI 상담 챗봇

청년 사용자의 개인 조건(나이, 지역, 취업 상태 등)을 기반으로, 신뢰 가능한 정책 문서만을 활용하여 허위 추천 없이 정확한 정책 정보를 제공하는 AI 상담 서비스입니다.

---

## 주요 기능

- **RAG 기반 정책 상담** — 벡터 DB에 저장된 정책 문서만 활용, 환각(Hallucination) 방지
- **세션 기반 사용자 정보 유지** — 나이·지역·취업 상태 등 자동 추출 및 DB 저장
- **멀티턴 대화** — 이전 대화 이력을 프롬프트에 반영한 맥락 유지
- **추천 표현 제어** — 조건 미확인 시 "추천합니다" 표현 금지, 대신 "적용 가능성 안내"
- **비정책 질문 필터링** — 날씨·맛집·연예인 등 무관한 질문 자동 차단
- **정책 분야** — 취업 / 주거 / 금융 / 창업 / 교육 / 복지

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React + Vite |
| Backend | FastAPI |
| LLM | OpenAI GPT-4o-mini |
| Embedding | OpenAI text-embedding-3-small |
| Vector DB | ChromaDB |
| DB | Supabase (PostgreSQL) |
| 배포 - Frontend | Vercel |
| 배포 - Backend | Railway |

---

## 시스템 아키텍처

```
사용자 (브라우저)
    ↓
React + Vite (Vercel)
    ↓ REST API
FastAPI (Railway)
    ├── 사용자 정보 추출 & 저장 → Supabase
    ├── 대화 이력 조회 → Supabase
    ├── 벡터 검색 (RAG) → ChromaDB
    └── LLM 호출 → OpenAI API
```

---

## 프로젝트 구조

```
youthfit/
├── backend/
│   ├── main.py              # FastAPI 서버 & 엔드포인트
│   ├── router.py            # 질문 분류 (ASK_CLARIFY / RAG_REWRITE / RAG_DIRECT)
│   ├── ingest.py            # 정책 문서 → ChromaDB 벡터화
│   ├── database.py          # DB 연결 & 쿼리
│   ├── user_service.py      # 사용자 정보 추출 & 저장
│   ├── clarify_service.py   # 추가 정보 요청 메시지 생성
│   ├── suggestion_service.py# 후속 질문 추천
│   ├── report/              # 정책 리포트 생성 모듈
│   ├── data/
│   │   ├── files/           # 원본 정책 문서 (CSV, TXT, PDF, Excel, JSON)
│   │   └── chroma_db/       # 벡터 DB (로컬 생성, git 제외)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # 메인 챗봇 UI
│   │   └── App.css
│   └── package.json
└── .claude/
    └── commands/            # Claude Code 슬래시 커맨드
```

---

## 로컬 실행

### 사전 준비

```bash
# .env 파일 생성 (backend/.env)
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://postgres:[비밀번호]@[supabase-host]:5432/postgres
```

> `DATABASE_URL`은 Supabase 대시보드 → Connect → Direct → URI에서 복사
> 로컬에서는 Session pooler URL 사용, 배포 시 Direct connection URL 사용

### 백엔드

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 정책 문서 벡터화 (최초 1회)
python ingest.py

# 서버 실행
uvicorn main:app --reload --port 8000
```

### 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

---

## 사용자 플로우

1. 사용자가 챗봇에 질문 입력
2. `user_id` 기반으로 사용자 정보 & 대화 이력 조회
3. Router가 질문 유형 분류
   - `ASK_CLARIFY` — 판정형 질문, 추가 정보 요청
   - `RAG_REWRITE` — 모호한 질문, 검색어 재정의 후 RAG
   - `RAG_DIRECT` — 문서 기반 직접 검색
4. ChromaDB에서 관련 정책 문서 검색
5. GPT-4o-mini가 문서 기반으로 답변 생성
6. 응답 DB 저장 & UI 출력

---

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/chat` | 챗봇 질문 처리 |
| POST | `/report/from_db` | DB 기반 리포트 생성 |
| GET | `/report/view` | 리포트 HTML 뷰 |
| POST | `/report/from_log` | 세션 로그 기반 리포트 생성 |
| GET | `/report/view_by_id` | 리포트 ID로 HTML 뷰 |
