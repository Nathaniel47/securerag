#!/bin/sh
# One container, two processes: the API on 8000 (internal) and the Streamlit UI on $PORT.
export PYTHONPATH="${PYTHONPATH:-.}"
uvicorn api.app:app --host 127.0.0.1 --port 8000 &
exec streamlit run ui/app.py --server.port="${PORT:-7860}" --server.address=0.0.0.0 \
  --server.headless=true --browser.gatherUsageStats=false
