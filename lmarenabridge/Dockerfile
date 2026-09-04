FROM python:3.11-slim
WORKDIR /app
COPY arena2api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mock_server.py ./mock_server.py
COPY real_server.py ./real_server.py
COPY arena2api/server.py ./server.py
# expose 8001 for bridge
EXPOSE 8001
ENV PORT=8001
# BRIDGE_MODE: mock (default) | real (direct arena.ai with token) | chrome (arena2api with extension)
CMD ["sh", "-c", "if [ \"$BRIDGE_MODE\" = \"real\" ]; then python real_server.py; elif [ \"$BRIDGE_MODE\" = \"chrome\" ]; then python server.py; else python -m uvicorn mock_server:app --host 0.0.0.0 --port 8001; fi"]
