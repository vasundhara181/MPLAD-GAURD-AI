# Build context is the repository root (see docker-compose.yml / the
# render.yaml dockerContext) so this can COPY both backend/ and the
# top-level data/ directory.

FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY data/ /data

ENV MPLAD_DATA_DIR=/data
ENV PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
