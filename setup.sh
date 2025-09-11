#!/bin/bash
set -e # 중간에 명령어가 실패하면 스크립트를 즉시 중단

# 1. Redis Stack 서버 설치 및 백그라운드 실행
echo ">>> Installing and starting Redis Stack Server..."
curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list > /dev/null
apt-get update
apt-get install -y redis-stack-server
redis-stack-server --daemonize yes
echo ">>> Redis Stack Server started."

# 2. Ollama 설치 및 백그라운드 실행
echo ">>> Installing and starting Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &

# Ollama 서버가 준비될 때까지 똑똑하게 대기
echo ">>> Waiting for Ollama server to be ready..."
timeout=120
start_time=$(date +%s)
while true; do
    if curl -s --head http://127.0.0.1:11434/ | head -n 1 | grep "200 OK" > /dev/null; then
        echo ">>> Ollama server is ready!"
        break
    fi
    current_time=$(date +%s)
    elapsed_time=$((current_time - start_time))
    if [ $elapsed_time -ge $timeout ]; then
        echo ">>> Timeout: Ollama server did not start within ${timeout} seconds."
        exit 1
    fi
    echo "    - Still waiting..."
    sleep 5
done

# --- [모델 업그레이드: Llama3-OpenBioLLM-8B Full Precision (FP16)] ---
# 3. Hugging Face Hub에서 Llama3-OpenBioLLM-8B FP16 GGUF 모델 다운로드
echo ">>> Downloading Llama3-OpenBioLLM-8B Full Precision (FP16) model... (This will be ~16.1GB)"
mkdir -p /models
# TheBloke/Llama3-OpenBioLLM-8B-GGUF 저장소의 F16 (무손실) 버전을 다운로드합니다.
wget https://huggingface.co/TheBloke/Llama3-OpenBioLLM-8B-GGUF/resolve/main/llama3-openbiollm-8b.F16.gguf -O /models/Llama3-OpenBioLLM-8B.F16.gguf
echo ">>> Model download complete."

# 4. Llama3-OpenBioLLM-8B FP16을 위한 Modelfile 동적 생성
echo ">>> Creating Modelfile for Llama3-OpenBioLLM-8B FP16..."
cat <<'EOF' > /models/Modelfile
FROM /models/Llama3-OpenBioLLM-8B.F16.gguf

# Llama 3 기반이므로, Llama 3의 프롬프트 템플릿을 사용합니다.
TEMPLATE """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

# 종료 토큰 설정
PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
EOF
echo ">>> Modelfile created."

# 5. Ollama를 이용해 커스텀 LLM 생성 (새로운 이름으로)
echo ">>> Creating 'biollama3-8b' model with Ollama..."
ollama create biollama3-8b -f /models/Modelfile
echo ">>> 'biollama3-8b' model created."
# --- [업그레이드 종료] ---

# 6. Ollama Hub에서 임베딩 모델 다운로드 (기존과 동일)
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

