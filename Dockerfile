FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/app SECURERAG_DAILY_LIVE_LIMIT=50
# CPU-only torch keeps the image small; sentence-transformers would otherwise pull the CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt
# Download the embedding model at build time so the first visitor does not wait for it.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
COPY . .
RUN useradd -m app && chown -R app /app
USER app
EXPOSE 7860
CMD ["sh", "start.sh"]
