새 정책 데이터를 추가하고 벡터 DB를 업데이트해줘.

순서:
1. backend/data/files/ 폴더에 어떤 파일이 있는지 목록 보여줘
2. 추가할 파일 형식 확인 (CSV / PDF / Excel)
3. 파일이 올바른 폴더에 있는지 확인
4. ingest.py 실행해서 벡터 DB 재구축
5. 완료 후 추가된 청크 수 알려줘

지원 형식: CSV, TXT, PDF, Excel(.xlsx), JSON
저장 위치: backend/data/files/
