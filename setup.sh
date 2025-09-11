#!/bin/bash
set -e # 중간에 명령어가 실패하면 스크립트를 즉시 중단

# 1. Redis Stack 서버 설치 및 백그라운드 실행 
echo ">>> Installing and starting Redis Stack Server..."
curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list
apt-get update
apt-get install -y redis-stack-server
redis-stack-server --daemonize yes
echo ">>> Redis Stack Server started."

# 2. Ollama 설치 및 백그라운드 실행
echo ">>> Installing and starting Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 15 # Ollama 서버가 완전히 켜질 때까지 15초 대기
echo ">>> Ollama Server started."

# 3. Hugging Face Hub에서 BioMistral GGUF 모델 다운로드
echo ">>> Downloading BioMistral model from Hugging Face..."
mkdir -p /models # 모델을 저장할 디렉토리 생성
wget https://huggingface.co/itlwas/BioMistral-7B-Q4_K_M-GGUF/resolve/main/biomistral-7b-q4_k_m.gguf -O /models/biomistral-7b.Q4_K_M.gguf
echo ">>> Model download complete."

# 4. VESSL 서버 내부에 Modelfile 동적 생성
echo ">>> Creating Modelfile for BioMistral..."
cat <<'EOF' > /models/Modelfile
FROM /models/biomistral-7b.Q4_K_M.gguf
TEMPLATE """[INST] {{ .Prompt }} [/INST]"""
SYSTEM """You are a world-class AI assistant for biomedical researchers. Your task is to generate accurate, professional, and reproducible lab notes based on the provided scientific context (SOPs). You must strictly adhere to the requested Markdown format. NEVER invent information. If the context is insufficient, state that clearly."""
PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_ctx 4096
EOF
echo ">>> Modelfile created."

# 5. Ollama를 이용해 커스텀 LLM 생성
echo ">>> Creating 'biomistral' model with Ollama..."
ollama create biomistral -f /models/Modelfile
echo ">>> 'biomistral' model created."

# 6. Ollama Hub에서 임베딩 모델 다운로드
echo ">>> Pulling 'nomic-embed-text' model from Ollama Hub..."
ollama pull nomic-embed-text
echo ">>> Embedding model pulled."

# 7. FastAPI 백엔드 종속성 설치
echo ">>> Setting up FastAPI backend..."
cd labnote-ai-backend
pip install -r requirements.txt
echo ">>> Backend dependencies installed."

# 8. FastAPI 서버 실행
echo ">>> Starting Uvicorn server on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000

