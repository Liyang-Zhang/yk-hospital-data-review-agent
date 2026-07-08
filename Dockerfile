FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SNAPSHOT_BACKEND=sqlite \
    SNAPSHOT_DB_URL=sqlite+pysqlite:////app/snapshot.db

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app
COPY docs ./docs

ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      --index-url ${PIP_INDEX_URL} \
      --trusted-host ${PIP_TRUSTED_HOST} \
      .

EXPOSE 8000

CMD ["uvicorn", "yk_review_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
