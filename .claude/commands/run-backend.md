FastAPI 백엔드 서버를 실행해줘.

순서:
1. backend/.env에 OPENAI_API_KEY가 있는지 키 이름만 확인
2. backend/ 디렉토리에서 아래 명령어 실행:
   uvicorn main:app --reload --port 8000
3. 서버가 뜨면 접속 URL 알려줘: http://localhost:8000

주요 엔드포인트:
- POST /chat — 챗봇 질문 처리
- GET /report/view — 리포트 뷰
- POST /report/from_db — DB 기반 리포트 생성
