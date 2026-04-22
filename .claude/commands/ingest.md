정책 문서를 벡터 DB에 재구축해줘.

순서:
1. backend/data/files/ 폴더에 어떤 파일이 있는지 확인 (CSV, PDF, Excel)
2. backend/ 디렉토리에서 `python ingest.py` 실행
3. 완료 후 저장된 청크 수 알려줘

참고:
- 임베딩 모델: OpenAI text-embedding-3-small
- 저장 위치: backend/data/chroma_db/
- OpenAI API 키가 backend/.env에 있어야 함
- 기존 chroma_db는 실행 시 자동 삭제 후 재생성됨
