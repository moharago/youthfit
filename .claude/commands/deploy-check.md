배포 전 체크리스트를 확인해줘. 각 항목을 직접 파일을 열어서 확인하고 OK / ❌ 로 결과 알려줘.

체크 항목:

[백엔드]
1. backend/main.py — ChatOllama 코드가 없고 ChatOpenAI 쓰고 있는지
2. backend/main.py — HuggingFaceEmbeddings 없고 OpenAIEmbeddings 쓰고 있는지
3. backend/requirements.txt — langchain-ollama, sentence-transformers, transformers 없는지
4. backend/.env — OPENAI_API_KEY 키가 존재하는지 (값은 보지 말 것)

[프론트엔드]
5. frontend/src/App.jsx — API URL이 하드코딩된 localhost인지, 환경변수로 처리됐는지
6. frontend/package.json — 정상적인 JSON인지 (비어있지 않은지)

[공통]
7. .gitignore — .env, node_modules, chroma_db, venv 포함됐는지
8. .claude/settings.local.json — .gitignore에 포함됐는지

결과 정리 후 ❌ 항목이 있으면 어떻게 고쳐야 하는지도 알려줘.
