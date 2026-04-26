FROM python:3.11-slim

WORKDIR /app

# 패키지 설치 (gcc는 빌드 후 제거)
COPY requirements.txt .
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y --auto-remove gcc && \
    rm -rf /var/lib/apt/lists/*

# 소스 복사
COPY . .

# 비루트 유저 생성 및 권한 설정
RUN useradd -u 1001 -m appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
