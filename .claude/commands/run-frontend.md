React 프론트엔드 개발 서버를 실행해줘.

순서:
1. frontend/package.json 확인해서 dev 스크립트 확인
2. node_modules 없으면 pnpm install 먼저 실행
3. frontend/ 디렉토리에서 실행:
   pnpm dev
4. 서버가 뜨면 접속 URL 알려줘 (기본: http://localhost:5173)

참고:
- 패키지 매니저: pnpm 사용
- API URL: VITE_API_URL 환경변수로 관리 (frontend/.env.local에 설정)
- 로컬 개발 시 기본값: http://localhost:8000 (백엔드)
- 백엔드 서버가 먼저 실행돼 있어야 챗봇이 작동함
- .env.local 예시: VITE_API_URL=http://localhost:8000
