#!/bin/bash
# This script sets up the complete AI backend environment on a VESSL Workspace.
# Version 3.3: Upgraded to the full-precision (F16) Llama3-OpenBioLLM-8B model for maximum performance.
set -e

# --- 1. System & Prerequisite Setup ---
echo ">>> Updating package lists and installing prerequisites..."
apt-get update > /dev/null
apt-get install -y curl > /dev/null
pip install -q huggingface_hub[cli]
echo ">>> Prerequisites installed."

# --- 2. Redis Stack Server Setup ---
echo ">>> Installing and starting Redis Stack Server..."
curl -fsSL https://packages.redis.io/gpg | gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/redis.list > /dev/null
apt-get update > /dev/null
apt-get install -y redis-stack-server > /dev/null
redis-stack-server --daemonize yes
echo ">>> Redis Stack Server started successfully."

# --- 3. Ollama Server Setup & Robust Wait ---
echo ">>> Installing and starting Ollama server..."
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
sleep 5

echo ">>> Waiting for Ollama server to be fully ready by pulling a small model..."
ollama pull nomic-embed-text
echo ">>> Ollama server is confirmed to be ready!"

# --- 4. Main LLM Download and Setup ---
echo ">>> Downloading Llama3-OpenBioLLM-8B (F16 Full Precision) model from mradermacher's repository..."
# ✅ 최고 성능의 무손실 원본(F16) 모델을 다운로드하도록 수정되었습니다.
huggingface-cli download mradermacher/Llama3-OpenBioLLM-8B-GGUF \
    Llama3-OpenBioLLM-8B.f16.gguf \
    --local-dir /models --local-dir-use-symlinks False
echo ">>> Model downloaded successfully."

# Create the Modelfile pointing to the downloaded model.
echo ">>> Creating Modelfile for 'biollama3'..."
cat <<'EOF' > /models/Modelfile
# ✅ 올바른 원본 파일명을 가리키도록 수정되었습니다.
FROM /models/Llama3-OpenBioLLM-8B.f16.gguf

# Llama 3 Instruct Template
TEMPLATE """<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{{ .System }}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{ .Prompt }}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

PARAMETER stop "<|eot_id|>"
PARAMETER stop "<|end_of_text|>"
EOF
echo ">>> Modelfile created."

# Create the custom model within Ollama.
echo ">>> Creating custom model 'biollama3' with Ollama..."
ollama create biollama3 -f /models/Modelfile
echo ">>> 'biollama3' model created successfully!"

# --- 5. FastAPI Backend Setup and Launch ---
echo ">>> Setting up FastAPI backend..."
cd labnote-ai-backend
pip install -r requirements.txt
echo ">>> Backend dependencies installed."

# Launch the FastAPI server.
echo ">>> Starting Uvicorn server on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000