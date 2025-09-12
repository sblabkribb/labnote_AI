#!/bin/bash
set -e

# 1. Redis Stack 서버 설치 및 실행 (기존 유지)
echo ">>> Installing and starting Redis Stack Server..."
curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list > /dev/null
apt-get update
apt-get install -y redis-stack-server
redis-stack-server --daemonize yes
echo ">>> Redis Stack Server started."

# 2. Ollama 설치 (기존 유지)
echo ">>> Installing and starting Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Ollama 서버 대기 (기존 유지)
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

# --- [핵심: OpenBioLLM-Llama3-70B Q8_0 다운로드 - mradermacher 저장소 사용] ---
echo ">>> Downloading OpenBioLLM-Llama3-70B Q8_0 model (2-part format) from mradermacher..."
mkdir -p /models

# ✅ 정확한 파일명으로 다운로드 (part1of2, part2of2)
huggingface-cli download mradermacher/OpenBioLLM-Llama3-70B-GGUF \
    OpenBioLLM-Llama3-70B.Q8_0.gguf.part1of2 \
    --local-dir /models --local-dir-use-symlinks False

huggingface-cli download mradermacher/OpenBioLLM-Llama3-70B-GGUF \
    OpenBioLLM-Llama3-70B.Q8_0.gguf.part2of2 \
    --local-dir /models --local-dir-use-symlinks False

# 파일 존재 확인 (중요!)
ls -la /models/OpenBioLLM-Llama3-70B.Q8_0.gguf.part*
if [ ! -f "/models/OpenBioLLM-Llama3-70B.Q8_0.gguf.part1of2" ] || [ ! -f "/models/OpenBioLLM-Llama3-70B.Q8_0.gguf.part2of2" ]; then
    echo "❌ ERROR: Required model files are missing!"
    exit 1
fi
echo "✅ Both parts downloaded successfully!"

# 4. Modelfile 생성 - 첫 번째 파트만 지정하면 Ollama가 자동으로 두 번째 찾음
echo ">>> Creating Modelfile for 'biollama3-70b'..."
cat <<'EOF' > /models/Modelfile
FROM /models/OpenBioLLM-Llama3-70B.Q8_0.gguf.part1of2

TEMPLATE """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
EOF
echo ">>> Modelfile created."

# 5. Ollama 모델 생성
echo ">>> Creating custom model 'biollama3-70b' with Ollama..."
ollama create biollama3-70b -f /models/Modelfile

# 확인
ollama list | grep biollama3-70b
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Model creation failed. Check Ollama logs with 'ollama serve' in another terminal."
    exit 1
fi
echo "✅ 'biollama3-70b' model created successfully!"

# 6. 임베딩 모델 다운로드 (기존 유지)
echo ">>> Pulling 'nomic-embed-text' embedding model..."
ollama pull nomic-embed-text

# 7. FastAPI 백엔드 설정 및 실행 (기존 유지)
echo ">>> Setting up FastAPI backend..."
cd labnote-ai-backend
pip install -r requirements.txt

# FastAPI 서버 실행
echo ">>> Starting Uvicorn server on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000