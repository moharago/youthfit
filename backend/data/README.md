# Data Directory
이 폴더는 RAG / 챗봇 프로젝트의 데이터 저장소입니다.

## 구조
- files/
  임베딩할 원본 문서 (CSV, PDF, TXT...)
  -> Git에 커밋하지 않음

- chroma_db/
  백터 데이터 베이스 (Chroma)
  -> ingest.py 실행 시 자동 생성
  -> Git에 커밋하지 않음
